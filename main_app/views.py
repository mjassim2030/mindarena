from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.db.models import Count, Q, F
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView
import os
from django.core.files.storage import default_storage
from django.utils.crypto import get_random_string
from django.db.utils import OperationalError, ProgrammingError
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import _short_code
CourseMember = None
from django.db.models import Prefetch
from django.contrib import messages

from .constants import (
    DEFAULT_ROLE,
    ROLE_SUPERUSER,
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_TEACHER,
    ROLE_STUDENT,
    ROLE_PARENTS,
)
from .forms import (
    SignUpForm,
    JoinOrganizationForm,
    OrgMemberCreateForm,
    OrgMemberEditForm,
    CourseCreateForm,
    CourseJoinForm,
    QuizCreateForm,
    QuizEditForm,
    QuestionForm,
    ChoiceFormSet,
)
from .models import (
    Organization,
    OrgMembership,
    Course,
    Quiz,
    LiveSession,
    LiveParticipant,
    LiveLeaderboard,
)
from .permissions import (
    allowed,
    ORG,
    MEMBERSHIP,
    COURSE,
    QUIZ,
    LIVE_SESSION,
    CREATE,
    READ_ALL,
    READ_ONE,
    UPDATE_ONE,
    DELETE_ONE,
)

User = get_user_model()


# --------------------
# Home / Auth
# --------------------
def home(request):
    if request.user.is_authenticated:
        return redirect("/dashboard/")

    # Safe stats (avoid 500 before migrate)
    try:
        stats = {
            "organizations": Organization.objects.count(),
            "users": User.objects.count(),
            "teachers": OrgMembership.objects.filter(role=ROLE_TEACHER).count(),
            "students": OrgMembership.objects.filter(role=ROLE_STUDENT).count(),
            "courses": Course.objects.count(),
            "quizzes": Quiz.objects.count(),
            "live_total": LiveSession.objects.count(),
            "live_active": LiveSession.objects.filter(ended_at__isnull=True).count(),
        }
    except (OperationalError, ProgrammingError):
        stats = {
            "organizations": 0,
            "users": 0,
            "teachers": 0,
            "students": 0,
            "courses": 0,
            "quizzes": 0,
            "live_total": 0,
            "live_active": 0,
        }

    return render(request, "home.html", {"stats": stats})


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            org = form.cleaned_data["organization"]
            OrgMembership.objects.create(organization=org, user=user, role=DEFAULT_ROLE)
            login(request, user)
            messages.success(request, "Welcome!")
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


def join_organization(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = JoinOrganizationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                org = form.create_organization()
                user = form.save(commit=False)
                user.email = form.cleaned_data["email"]
                user.save()
                OrgMembership.objects.create(organization=org, user=user, role=ROLE_ADMIN)
            login(request, user)
            messages.success(request, "Organization created and you are set as Admin.")
            return redirect("/")
    else:
        form = JoinOrganizationForm()

    return render(request, "registration/join_organization.html", {"form": form})


class SignInView(LoginView):
    template_name = "registration/login.html"


class SignOutView(LogoutView):
    next_page = "/login/"


# --------------------
# Helpers
# --------------------
def _actor_role_and_org(user):
    if user.is_superuser:
        return ROLE_SUPERUSER, None
    m = OrgMembership.objects.select_related("organization").filter(user=user).first()
    if not m:
        return None, None
    return m.role, m.organization


def _broadcast(session_id: int, payload: dict):
    # Legacy helper (unused by the new UI), kept for compatibility
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"live_{session_id}",
        {"type": "live.event", "payload": payload},
    )


def _serialize_session_for_course(session):
    d = dict(session.details or {})
    return {
        "id": session.id,
        "quiz_title": session.quiz.quiz_title,
        "host_name": session.host.get_full_name() or session.host.username,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "join_code": d.get("join_code"),
    }


# --- Realtime helpers (course + live groups) ---
def _course_group_send(course_id: int, payload: dict):
    """Send to everyone on the course detail page."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"course_{course_id}",
        {"type": "course.update", "payload": payload},
    )


def _live_update_send(session_id: int, payload: dict):
    """Send a state update to everyone on the live session page (and the host’s detail page)."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"live_{session_id}",
        {"type": "session.update", "payload": payload},
    )


def _live_event_send(session_id: int, payload: dict):
    """Send a one-off event (e.g., started, question_changed)."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"live_{session_id}",
        {"type": "session.event", "payload": payload},
    )


def _participants_rows_for_ws(session: LiveSession):
    """Participants for the table JS (excluding host)."""
    return list(
        LiveParticipant.objects.select_related("user")
        .filter(livesession=session)
        .exclude(user_id=session.host_id)
        .annotate(
            username=F("user__username"),
            first_name=F("user__first_name"),
            last_name=F("user__last_name"),
            email=F("user__email"),
        )
        .values("user_id", "username", "first_name", "last_name", "email")
    )


def _lobby_users_rows_for_ws(session: LiveSession):
    """Lobby users with fields expected by the table JS, preserving order."""
    ids = list((session.details or {}).get("lobby", []))
    if not ids:
        return []
    by_id = {
        u["id"]: u
        for u in User.objects.filter(id__in=ids).values("id", "username", "first_name", "last_name", "email")
    }
    return [by_id[i] for i in ids if i in by_id]


def _leaderboard_rows_for_ws(session: LiveSession):
    """Leaderboard rows with fields expected by the table JS."""
    return list(
        LiveLeaderboard.objects.select_related("participant", "participant__user")
        .filter(livesession=session)
        .order_by("rank")
        .values(
            "rank",
            "score",
            username=F("participant__user__username"),
            first_name=F("participant__user__first_name"),
            last_name=F("participant__user__last_name"),
        )
    )


def _compute_runtime_leaderboard(session: LiveSession):
    rows = []
    qs = LiveParticipant.objects.select_related("user").filter(livesession=session)
    for p in qs:
        answers = p.answer_questions or []
        score = sum(int(a.get("points", 0)) for a in answers)
        rows.append({"participant": p, "score": score})
    rows.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


def _ensure_can_edit_quiz(request, quiz: Quiz):
    role, _ = _actor_role_and_org(request.user)
    if role is None:
        return False
    if role == ROLE_SUPERUSER:
        return True
    if not allowed(request.user, UPDATE_ONE, QUIZ, org=quiz.course.organization):
        return False
    if role == ROLE_TEACHER and quiz.course.teacher_id != request.user.id:
        return False
    return True


def _get_content_list(quiz: Quiz):
    data = list(quiz.content or [])
    out = []
    for d in data:
        out.append(
            {
                "question": d.get("question") or d.get("Question") or "",
                "question_type": (d.get("question_type") or d.get("QuestionType") or "MCQ").upper(),
                "image": d.get("image"),
                "choices": d.get("choices") or d.get("Choices") or [],
            }
        )
    return out


def _save_content_list(quiz: Quiz, content_list):
    quiz.content = content_list
    quiz.save(update_fields=["content"])


def _save_uploaded_image(file) -> str:
    ext = os.path.splitext(file.name)[1].lower() or ".jpg"
    name = f"quiz_images/{timezone.now().strftime('%Y%m%d')}_{get_random_string(8)}{ext}"
    path = default_storage.save(name, file)
    return default_storage.url(path)


# --------------------
# Dashboard
# --------------------
@login_required
def dashboard(request):
    user = request.user

    if user.is_superuser:
        role, org = ROLE_SUPERUSER, None
    else:
        mem = OrgMembership.objects.select_related("organization").filter(user=user).first()
        if not mem:
            return render(request, "main_app/dashboard_empty.html")
        role, org = mem.role, mem.organization

    ctx = {"role": role, "org": org, "title": "Dashboard"}

    # -------------------------
    # SUPERUSER (global)
    # -------------------------
    if role == ROLE_SUPERUSER:
        ctx["title"] = "Dashboard (Superuser)"

        total_orgs = Organization.objects.count()
        total_users = User.objects.count()
        total_courses = Course.objects.count()
        total_quizzes = Quiz.objects.count()
        total_live_ongoing = LiveSession.objects.filter(ended_at__isnull=True).count()
        total_teachers = OrgMembership.objects.filter(role=ROLE_TEACHER).count()
        total_students = OrgMembership.objects.filter(role=ROLE_STUDENT).count()

        org_rollups = Organization.objects.order_by("name").annotate(
            members=Count("memberships"),
            teachers=Count("memberships", filter=Q(memberships__role=ROLE_TEACHER)),
            students=Count("memberships", filter=Q(memberships__role=ROLE_STUDENT)),
        )

        live_rows = (
            LiveSession.objects.select_related("quiz", "host", "quiz__course", "quiz__course__organization")
            .filter(ended_at__isnull=True)
            .order_by("-id")[:12]
        )
        ctx["cards"] = {
            "ORGANIZATIONS": total_orgs,
            "USERS": total_users,
            "COURSES": total_courses,
            "QUIZZES": total_quizzes,
            "TEACHERS": total_teachers,
            "LIVE_SESSIONS": total_live_ongoing,
            "STUDENTS": total_students,
        }
        ctx["lists"] = {
            "Org members": [f"{o.name} — {o.members}" for o in org_rollups],
            "Teachers per organization": [f"{o.name} — {o.teachers}" for o in org_rollups],
            "Students per organization": [f"{o.name} — {o.students}" for o in org_rollups],
            "Live_sessions_ongoing": [
                f"#{s.id} — {s.quiz.quiz_title} — {s.quiz.course.course_name} — host: {(s.host.get_full_name() or s.host.username)}"
                for s in live_rows
            ],
        }
        ctx["actions"] = {
            "create_orgmember_any_org": True,
            "manage_courses_global": True,
            "manage_quizzes_global": True,
            "manage_lives_global": True,
        }
        return render(request, "main_app/dashboard.html", ctx)

    # -------------------------
    # ADMIN / MANAGER (org scoped)
    # -------------------------
    if role in {ROLE_ADMIN, ROLE_MANAGER}:
        ctx["title"] = f"Dashboard ({role.capitalize()})"

        org_courses = Course.objects.filter(organization=org)
        org_quizzes = Quiz.objects.filter(course__organization=org)
        org_live_ongoing = LiveSession.objects.filter(quiz__course__organization=org, ended_at__isnull=True)

        org_members_qs = (
            OrgMembership.objects.select_related("user")
            .filter(organization=org)
            .only(
                "id",
                "role",
                "user__username",
                "user__email",
                "user__first_name",
                "user__last_name",
            )
        )

        total_org_members = org_members_qs.count()
        total_teachers = org_members_qs.filter(role=ROLE_TEACHER).count()
        total_students = org_members_qs.filter(role=ROLE_STUDENT).count()

        teachers_qs = org_members_qs.filter(role=ROLE_TEACHER).order_by("user__username")
        students_qs = org_members_qs.filter(role=ROLE_STUDENT).order_by("user__username")

        live_rows = (
            org_live_ongoing.select_related("quiz", "host", "quiz__course")
            .order_by("-id")[:12]
        )

        ctx["cards"] = {
            "ORG_MEMBERS": total_org_members,
            "COURSES": org_courses.count(),
            "QUIZZES": org_quizzes.count(),
            "TEACHERS": total_teachers,
            "LIVE_SESSIONS": org_live_ongoing.count(),
            "STUDENTS": total_students,
        }
        ctx["lists"] = {
            "Live_sessions_ongoing": [
                f"#{s.id} — {s.quiz.quiz_title} — {s.quiz.course.course_name} — host: {(s.host.get_full_name() or s.host.username)}"
                for s in live_rows
            ],
        }
        ctx["teachers"] = teachers_qs
        ctx["students"] = students_qs
        ctx["actions"] = {
            "create_orgmember_this_org": True,
            "manage_courses": True,
            "manage_quizzes": True,
            "manage_lives": True,
        }
        return render(request, "main_app/dashboard.html", ctx)

    # -------------------------
    # TEACHER
    # -------------------------
    if role == ROLE_TEACHER:
        teacher_courses = Course.objects.filter(organization=org, teacher=user)
        teacher_quizzes = Quiz.objects.filter(course__organization=org, course__teacher=user)
        teacher_live_ongoing = LiveSession.objects.filter(
            quiz__course__organization=org,
            host=user,
            ended_at__isnull=True
        )

        live_rows = (
            teacher_live_ongoing.select_related("quiz", "quiz__course")
            .order_by("-id")[:12]
        )

        ctx["title"] = "Dashboard (Teacher)"
        ctx["cards"] = {
            "COURSES": teacher_courses.count(),
            "QUIZZES": teacher_quizzes.count(),
            "MY_QUIZZES": teacher_quizzes.count(),
            "LIVE_SESSIONS": teacher_live_ongoing.count(),
        }
        ctx["lists"] = {
            "My_courses": [c.course_name for c in teacher_courses.order_by("course_name")[:12]],
            "Live_sessions_ongoing": [
                f"#{s.id} — {s.quiz.quiz_title} — {s.quiz.course.course_name}"
                for s in live_rows
            ],
        }
        ctx["actions"] = {"manage_quizzes": True, "manage_lives": True}
        return render(request, "main_app/dashboard.html", ctx)

    # -------------------------
    # STUDENT
    # -------------------------
    if role == ROLE_STUDENT:
        # Prefer enrolled courses if you have CourseMember
        if CourseMember is not None:
            enrolled = CourseMember.objects.select_related("course").filter(
                user=user, course__organization=org
            )
            courses_qs = Course.objects.filter(id__in=enrolled.values("course_id"))
        else:
            # Fallback: show all org courses (if you don't track enrollment)
            courses_qs = Course.objects.filter(organization=org)

        quizzes_qs = Quiz.objects.filter(course__in=courses_qs)
        live_ongoing_qs = LiveSession.objects.filter(
            quiz__course__in=courses_qs,
            ended_at__isnull=True
        )

        ctx["title"] = "Dashboard (Student)"
        ctx["cards"] = {
            "COURSES": courses_qs.count(),
            "QUIZZES": quizzes_qs.count(),
            "LIVE_SESSIONS": live_ongoing_qs.count(),
        }
        ctx["lists"] = {
            "Courses": [c.course_name for c in courses_qs.order_by("course_name")[:12]],
            "Live_sessions_ongoing": [
                f"#{s.id} — {s.quiz.quiz_title} — {s.quiz.course.course_name}"
                for s in live_ongoing_qs.select_related("quiz", "quiz__course").order_by("-id")[:12]
            ],
        }
        ctx["actions"] = {}
        return render(request, "main_app/dashboard.html", ctx)

    # -------------------------
    # PARENTS
    # -------------------------
    if role == ROLE_PARENTS:
        # If you later model parent->child relations, scope these to the child’s courses.
        courses_qs = Course.objects.filter(organization=org)
        quizzes_qs = Quiz.objects.filter(course__organization=org)
        live_ongoing_qs = LiveSession.objects.filter(quiz__course__organization=org, ended_at__isnull=True)

        ctx["title"] = "Dashboard (Parents)"
        ctx["cards"] = {
            "COURSES": courses_qs.count(),
            "QUIZZES": quizzes_qs.count(),
            "LIVE_SESSIONS": live_ongoing_qs.count(),
        }
        ctx["lists"] = {
            "Courses": [c.course_name for c in courses_qs.order_by("course_name")[:12]],
            "Live_sessions_ongoing": [
                f"#{s.id} — {s.quiz.quiz_title} — {s.quiz.course.course_name}"
                for s in live_ongoing_qs.select_related("quiz", "quiz__course").order_by("-id")[:12]
            ],
            # keep your extra sections for badges/xp if you later populate them
            "Children_badges": [],
            "Children_xp": [],
        }
        ctx["actions"] = {}
        return render(request, "main_app/dashboard.html", ctx)

    # Fallback
    ctx["cards"], ctx["lists"], ctx["actions"] = {}, {}, {}
    return render(request, "main_app/dashboard.html", ctx)


# --------------------
# Organizations
# --------------------
@login_required
def orgmember_create(request):
    if request.user.is_superuser:
        actor_role, actor_org = ROLE_SUPERUSER, None
    else:
        m = OrgMembership.objects.select_related("organization").filter(user=request.user).first()
        if not m:
            messages.error(request, "You are not in any organization.")
            return redirect("/dashboard/")
        actor_role, actor_org = m.role, m.organization

    if not allowed(request.user, CREATE, MEMBERSHIP, org=actor_org or Organization.objects.first()):
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = OrgMemberCreateForm(request.POST)
        if actor_role in {ROLE_ADMIN, ROLE_MANAGER}:
            form.fields["organization"].required = False

        if form.is_valid():
            with transaction.atomic():
                org = form.cleaned_data["organization"] if request.user.is_superuser else actor_org
                if org is None:
                    messages.error(request, "Organization is required.")
                    return render(
                        request,
                        "main_app/orgmember_form.html",
                        {"form": form, "actor_role": actor_role, "actor_org": actor_org},
                    )

                role = form.cleaned_data["role"]
                username = form.cleaned_data["username"]
                email = form.cleaned_data["email"]
                password = form.cleaned_data["password"]

                user = User.objects.filter(email__iexact=email).first()
                if user is None:
                    user = User(username=username, email=email)
                    if password:
                        user.set_password(password)
                    else:
                        user.set_unusable_password()
                    user.save()
                else:
                    if user.username != username and not User.objects.filter(username=username).exclude(pk=user.pk).exists():
                        user.username = username
                        user.save()
                    if password:
                        user.set_password(password)
                        user.save()

                obj, created = OrgMembership.objects.get_or_create(
                    organization=org, user=user, defaults={"role": role}
                )
                if not created:
                    obj.role = role
                    obj.save()

            messages.success(request, f"Member added to {org.name} as {role}.")
            return redirect("dashboard")
    else:
        form = OrgMemberCreateForm()
        if actor_role in {ROLE_ADMIN, ROLE_MANAGER}:
            form.fields["organization"].widget = forms.HiddenInput()
            form.initial["organization"] = actor_org.pk

    return render(
        request,
        "main_app/orgmember_form.html",
        {"form": form, "actor_role": actor_role, "actor_org": actor_org},
    )


@login_required
def orgmember_edit(request, pk: int):
    membership = get_object_or_404(OrgMembership.objects.select_related("user", "organization"), pk=pk)
    org = membership.organization

    if not allowed(request.user, UPDATE_ONE, MEMBERSHIP, org=org):
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = OrgMemberEditForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                u = membership.user
                username = form.cleaned_data["username"]
                email = form.cleaned_data["email"]
                password = form.cleaned_data["password"]

                if u.username != username and not User.objects.filter(username=username).exclude(pk=u.pk).exists():
                    u.username = username
                u.email = email
                if password:
                    u.set_password(password)
                u.save()

                membership.role = form.cleaned_data["role"]
                membership.save()

            messages.success(request, "Member updated.")
            return redirect("dashboard")
    else:
        form = OrgMemberEditForm()
        form.initialize_from_membership(membership)

    return render(request, "main_app/orgmember_edit.html", {"membership": membership, "form": form})


@login_required
def orgmember_delete(request, pk: int):
    membership = get_object_or_404(OrgMembership.objects.select_related("user", "organization"), pk=pk)
    org = membership.organization

    if not allowed(request.user, DELETE_ONE, MEMBERSHIP, org=org):
        return render(request, "403.html", status=403)

    if request.method == "POST":
        username = membership.user.username
        membership.delete()
        messages.success(request, f"{username} removed from {org.name}.")
        return redirect("dashboard")

    return render(request, "main_app/orgmember_confirm_delete.html", {"membership": membership})


class OrganizationListView(ListView):
    model = Organization
    template_name = "main_app/organizations_list.html"
    context_object_name = "organizations"
    ordering = ["name"]

    def dispatch(self, request, *args, **kwargs):
        if not allowed(request.user, READ_ALL, ORG):
            return HttpResponseForbidden("Not allowed")
        return super().dispatch(request, *args, **kwargs)


# --------------------
# Courses
# --------------------
@login_required
def course_list(request):
    role, org = _actor_role_and_org(request.user)
    if role is None:
        return render(request, "main_app/dashboard_empty.html")

    if role == ROLE_SUPERUSER:
        qs = Course.objects.select_related("organization", "teacher").order_by("course_name")
    else:
        if not allowed(request.user, READ_ALL, COURSE, org=org):
            return render(request, "403.html", status=403)
        base = Course.objects.select_related("organization", "teacher").filter(organization=org)
        if role in {ROLE_ADMIN, ROLE_MANAGER}:
            qs = base
        elif role == ROLE_TEACHER:
            qs = base.filter(teacher=request.user)
        else:
            qs = [c for c in base if request.user.id in (c.enrolled_students or [])]

    can_create = allowed(request.user, CREATE, COURSE, org=org)
    return render(
        request,
        "main_app/course_list.html",
        {"courses": qs, "role": role, "org": org, "can_create": can_create},
    )


@login_required
def course_create(request):
    role, org = _actor_role_and_org(request.user)

    target_org = org
    if role != ROLE_SUPERUSER and not allowed(request.user, CREATE, COURSE, org=target_org):
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = CourseCreateForm(request.POST, actor_role=role, actor_org=org)
        if form.is_valid():
            with transaction.atomic():
                org_obj = form.cleaned_org()
                teacher = form.cleaned_teacher(org_obj)
                course = Course.objects.create(
                    organization=org_obj,
                    teacher=teacher,
                    course_name=form.cleaned_data["course_name"],
                    join_code=form.cleaned_data["join_code"],
                    subject_category=form.cleaned_data["subject_category"],
                    enrolled_students=[],
                )
            messages.success(request, "Course created.")
            return redirect("course_detail", pk=course.pk)
    else:
        form = CourseCreateForm(actor_role=role, actor_org=org)

    return render(request, "main_app/course_form.html", {"form": form, "org": org, "role": role})


@login_required
def course_detail(request, pk: int):
    course = get_object_or_404(Course.objects.select_related("organization", "teacher"), pk=pk)
    role, org = _actor_role_and_org(request.user)

    if role != ROLE_SUPERUSER and not allowed(request.user, READ_ONE, COURSE, org=course.organization):
        return render(request, "403.html", status=403)
    if role == ROLE_TEACHER and course.teacher_id != request.user.id:
        return render(request, "403.html", status=403)
    if role in {ROLE_STUDENT, ROLE_PARENTS} and request.user.id not in (course.enrolled_students or []):
        return render(request, "403.html", status=403)

    # Keep realtime table (ongoing only) for the top section
    ongoing_sessions = (
        LiveSession.objects
        .select_related("host", "quiz")
        .filter(quiz__course=course, ended_at__isnull=True)
        .order_by("-id")
    )

    # Quizzes for this course (static nesting section)
    quizzes = list(Quiz.objects.filter(course=course).order_by("quiz_title"))

    # Fetch all sessions for these quizzes in one query and bucket them
    if quizzes:
        quiz_ids = [q.id for q in quizzes]
        sessions = (
            LiveSession.objects
            .select_related("host")
            .filter(quiz_id__in=quiz_ids)
            .order_by("-id")
        )
        by_quiz = {}
        for s in sessions:
            by_quiz.setdefault(s.quiz_id, []).append(s)
        # Attach to each quiz so the template can do: q.sessions_for_list
        for q in quizzes:
            q.sessions_for_list = by_quiz.get(q.id, [])
    else:
        for q in quizzes:
            q.sessions_for_list = []

    return render(
        request,
        "main_app/course_detail.html",
        {
            "course": course,
            "role": role,
            "ongoing_sessions": ongoing_sessions,  # used by your realtime table + WS
            "quizzes": quizzes,                    # each quiz has q.sessions_for_list
        },
    )


@login_required
def course_join(request):
    role, org = _actor_role_and_org(request.user)
    if role != ROLE_STUDENT or org is None:
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = CourseJoinForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["join_code"].strip()
            course = Course.objects.filter(join_code=code).first()
            if not course:
                messages.error(request, "Invalid join code.")
                return render(request, "main_app/course_join.html", {"form": form})
            if course.organization_id != org.id:
                messages.error(request, "You can only join courses in your organization.")
                return render(request, "main_app/course_join.html", {"form": form})

            enrolled = list(course.enrolled_students or [])
            if request.user.id not in enrolled:
                enrolled.append(request.user.id)
                course.enrolled_students = enrolled
                course.save(update_fields=["enrolled_students"])

            messages.success(request, f"You joined {course.course_name}.")
            return redirect("course_detail", pk=course.pk)
    else:
        form = CourseJoinForm()

    return render(request, "main_app/course_join.html", {"form": form})


# --------------------
# Quizzes
# --------------------
@login_required
def quiz_list(request):
    role, org = _actor_role_and_org(request.user)
    if role is None:
        return render(request, "main_app/dashboard_empty.html")

    if role == ROLE_SUPERUSER:
        qs = Quiz.objects.select_related("course", "course__organization", "course__teacher").order_by("quiz_title")
    else:
        if not allowed(request.user, READ_ALL, QUIZ, org=org):
            return render(request, "403.html", status=403)
        base = Quiz.objects.select_related("course", "course__organization", "course__teacher").filter(
            course__organization=org
        )
        if role in {ROLE_ADMIN, ROLE_MANAGER}:
            qs = base
        elif role == ROLE_TEACHER:
            qs = base.filter(course__teacher=request.user)
        else:
            courses = Course.objects.filter(organization=org).select_related("teacher")
            joined = [c.id for c in courses if request.user.id in (c.enrolled_students or [])]
            qs = base.filter(course_id__in=joined)

    can_create = allowed(request.user, CREATE, QUIZ, org=org)
    return render(
        request,
        "main_app/quiz_list.html",
        {"quizzes": qs, "role": role, "org": org, "can_create": can_create},
    )


@login_required
def quiz_detail(request, pk: int):
    quiz = get_object_or_404(Quiz.objects.select_related("course", "course__organization", "course__teacher"), pk=pk)
    role, _ = _actor_role_and_org(request.user)

    if role != ROLE_SUPERUSER and not allowed(request.user, READ_ONE, QUIZ, org=quiz.course.organization):
        return render(request, "403.html", status=403)
    if role == ROLE_TEACHER and quiz.course.teacher_id != request.user.id:
        return render(request, "403.html", status=403)
    if role in {ROLE_STUDENT, ROLE_PARENTS} and request.user.id not in (quiz.course.enrolled_students or []):
        return render(request, "403.html", status=403)

    can_edit = allowed(request.user, UPDATE_ONE, QUIZ, org=quiz.course.organization) and (
        role != ROLE_TEACHER or quiz.course.teacher_id == request.user.id
    )
    can_delete = allowed(request.user, DELETE_ONE, QUIZ, org=quiz.course.organization) and (
        role != ROLE_TEACHER or quiz.course.teacher_id == request.user.id
    )

    return render(
        request,
        "main_app/quiz_detail.html",
        {"quiz": quiz, "role": role, "can_edit": can_edit, "can_delete": can_delete},
    )


@login_required
def quiz_create(request):
    role, org = _actor_role_and_org(request.user)
    if role is None:
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = QuizCreateForm(request.POST, actor_role=role, actor_org=org, actor_user=request.user)
        if form.is_valid():
            course = form.cleaned_data["course"]
            if role != ROLE_SUPERUSER and not allowed(request.user, CREATE, QUIZ, org=course.organization):
                return render(request, "403.html", status=403)
            if role == ROLE_TEACHER and course.teacher_id != request.user.id:
                return render(request, "403.html", status=403)

            quiz = Quiz.objects.create(course=course, quiz_title=form.cleaned_data["quiz_title"], content=[])
            messages.success(request, "Quiz created.")
            return redirect("quiz_detail", pk=quiz.pk)
    else:
        form = QuizCreateForm(actor_role=role, actor_org=org, actor_user=request.user)

    return render(request, "main_app/quiz_form.html", {"form": form, "org": org, "role": role})


@login_required
def quiz_edit(request, pk: int):
    quiz = get_object_or_404(Quiz.objects.select_related("course", "course__organization", "course__teacher"), pk=pk)
    role, org = _actor_role_and_org(request.user)

    if role != ROLE_SUPERUSER and not allowed(request.user, UPDATE_ONE, QUIZ, org=quiz.course.organization):
        return render(request, "403.html", status=403)
    if role == ROLE_TEACHER and quiz.course.teacher_id != request.user.id:
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = QuizEditForm(request.POST, actor_role=role, actor_org=org, actor_user=request.user, instance=quiz)
        if form.is_valid():
            new_course = form.cleaned_data["course"]
            new_title = form.cleaned_data["quiz_title"]

            if role != ROLE_SUPERUSER and not allowed(request.user, UPDATE_ONE, QUIZ, org=new_course.organization):
                return render(request, "403.html", status=403)
            if role == ROLE_TEACHER and new_course.teacher_id != request.user.id:
                return render(request, "403.html", status=403)

            quiz.course = new_course
            quiz.quiz_title = new_title
            quiz.save(update_fields=["course", "quiz_title"])
            messages.success(request, "Quiz updated.")
            return redirect("quiz_detail", pk=quiz.pk)
    else:
        form = QuizEditForm(actor_role=role, actor_org=org, actor_user=request.user, instance=quiz)

    return render(request, "main_app/quiz_form_edit.html", {"form": form, "quiz": quiz})


@login_required
def quiz_delete(request, pk: int):
    quiz = get_object_or_404(Quiz.objects.select_related("course", "course__organization", "course__teacher"), pk=pk)
    role, _ = _actor_role_and_org(request.user)

    if role != ROLE_SUPERUSER and not allowed(request.user, DELETE_ONE, QUIZ, org=quiz.course.organization):
        return render(request, "403.html", status=403)
    if role == ROLE_TEACHER and quiz.course.teacher_id != request.user.id:
        return render(request, "403.html", status=403)

    if request.method == "POST":
        quiz.delete()
        messages.success(request, "Quiz deleted.")
        return redirect("quiz_list")

    return render(request, "main_app/quiz_confirm_delete.html", {"quiz": quiz})


@login_required
def quiz_questions(request, pk: int):
    quiz = get_object_or_404(Quiz.objects.select_related("course", "course__organization", "course__teacher"), pk=pk)
    if not _ensure_can_edit_quiz(request, quiz):
        return render(request, "403.html", status=403)

    questions = _get_content_list(quiz)
    return render(request, "main_app/quiz_questions.html", {"quiz": quiz, "questions": questions})


@login_required
def quiz_question_add(request, pk: int):
    quiz = get_object_or_404(Quiz.objects.select_related("course", "course__organization", "course__teacher"), pk=pk)
    if not _ensure_can_edit_quiz(request, quiz):
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = QuestionForm(request.POST, request.FILES)
        formset = ChoiceFormSet(request.POST, prefix="c")
        if form.is_valid():
            qtype = form.cleaned_data["question_type"]
            img_file = form.cleaned_data.get("image")
            image_url = _save_uploaded_image(img_file) if img_file else None
            text = form.cleaned_data["question"]

            if qtype == "TF":
                corr = form.cleaned_data.get("correct_tf") or "T"
                choices = [{"text": "True", "is_correct": corr == "T"},
                           {"text": "False", "is_correct": corr == "F"}]
            else:
                if not formset.is_valid():
                    return render(request, "main_app/quiz_question_form.html",
                                  {"quiz": quiz, "form": form, "formset": formset, "mode": "add"})
                rows = [f.cleaned_data for f in formset.forms if f.cleaned_data and not f.cleaned_data.get("DELETE")]
                rows = [r for r in rows if r.get("text")]
                if len(rows) < 2:
                    form.add_error(None, "Please add at least two choices.")
                    return render(request, "main_app/quiz_question_form.html",
                                  {"quiz": quiz, "form": form, "formset": formset, "mode": "add"})
                if qtype == "MCQ" and sum(1 for r in rows if r.get("is_correct")) != 1:
                    form.add_error(None, "For MCQ, mark exactly one choice as correct.")
                    return render(request, "main_app/quiz_question_form.html",
                                  {"quiz": quiz, "form": form, "formset": formset, "mode": "add"})
                if qtype == "MSQ" and sum(1 for r in rows if r.get("is_correct")) < 1:
                    form.add_error(None, "For MSQ, mark one or more choices as correct.")
                    return render(request, "main_app/quiz_question_form.html",
                                  {"quiz": quiz, "form": form, "formset": formset, "mode": "add"})
                choices = [{"text": r["text"], "is_correct": bool(r.get("is_correct"))} for r in rows]

            qobj = {"question_type": qtype, "image": image_url, "question": text, "choices": choices}
            data = _get_content_list(quiz)
            data.append(qobj)
            _save_content_list(quiz, data)
            messages.success(request, "Question added.")
            return redirect("quiz_questions", pk=quiz.pk)
    else:
        form = QuestionForm(initial={"question_type": "MCQ"})
        formset = ChoiceFormSet(prefix="c")

    return render(request, "main_app/quiz_question_form.html",
                  {"quiz": quiz, "form": form, "formset": formset, "mode": "add"})


@login_required
def quiz_question_edit(request, pk: int, qindex: int):
    quiz = get_object_or_404(Quiz.objects.select_related("course", "course__organization", "course__teacher"), pk=pk)
    if not _ensure_can_edit_quiz(request, quiz):
        return render(request, "403.html", status=403)

    data = _get_content_list(quiz)
    if not (0 <= qindex < len(data)):
        return render(request, "404.html", status=404)
    q = data[qindex]

    if request.method == "POST":
        form = QuestionForm(request.POST, request.FILES)
        formset = ChoiceFormSet(request.POST, prefix="c")
        if form.is_valid():
            qtype = form.cleaned_data["question_type"]
            img_file = form.cleaned_data.get("image")
            image_url = _save_uploaded_image(img_file) if img_file else (q.get("image") or None)
            text = form.cleaned_data["question"]

            if qtype == "TF":
                corr = form.cleaned_data.get("correct_tf") or "T"
                choices = [{"text": "True", "is_correct": corr == "T"},
                           {"text": "False", "is_correct": corr == "F"}]
            else:
                if not formset.is_valid():
                    return render(request, "main_app/quiz_question_form.html",
                                  {"quiz": quiz, "form": form, "formset": formset, "mode": "edit", "qindex": qindex})
                rows = [f.cleaned_data for f in formset.forms if f.cleaned_data and not f.cleaned_data.get("DELETE")]
                rows = [r for r in rows if r.get("text")]
                if len(rows) < 2:
                    form.add_error(None, "Please add at least two choices.")
                    return render(request, "main_app/quiz_question_form.html",
                                  {"quiz": quiz, "form": form, "formset": formset, "mode": "edit", "qindex": qindex})
                if qtype == "MCQ" and sum(1 for r in rows if r.get("is_correct")) != 1:
                    form.add_error(None, "For MCQ, mark exactly one choice as correct.")
                    return render(request, "main_app/quiz_question_form.html",
                                  {"quiz": quiz, "form": form, "formset": formset, "mode": "edit", "qindex": qindex})
                if qtype == "MSQ" and sum(1 for r in rows if r.get("is_correct")) < 1:
                    form.add_error(None, "For MSQ, mark one or more choices as correct.")
                    return render(request, "main_app/quiz_question_form.html",
                                  {"quiz": quiz, "form": form, "formset": formset, "mode": "edit", "qindex": qindex})
                choices = [{"text": r["text"], "is_correct": bool(r.get("is_correct"))} for r in rows]

            qnew = {"question_type": qtype, "image": image_url, "question": text, "choices": choices}
            data[qindex] = qnew
            _save_content_list(quiz, data)
            messages.success(request, "Question updated.")
            return redirect("quiz_questions", pk=quiz.pk)
    else:
        init = {
            "question_type": (q.get("question_type") or "MCQ").upper(),
            "question": q.get("question") or "",
        }
        form = QuestionForm(initial=init)
        if init["question_type"] == "TF":
            ch = q.get("choices") or []
            corr_T = bool(ch and ch[0].get("is_correct"))
            form.initial["correct_tf"] = "T" if corr_T else "F"
            formset = ChoiceFormSet(prefix="c", initial=[])
        else:
            init_choices = [{"text": c.get("text", ""), "is_correct": bool(c.get("is_correct"))}
                            for c in (q.get("choices") or [])]
            formset = ChoiceFormSet(prefix="c", initial=init_choices)

    return render(request, "main_app/quiz_question_form.html",
                  {"quiz": quiz, "form": form, "formset": formset, "mode": "edit", "qindex": qindex})


@login_required
def quiz_question_delete(request, pk: int, qindex: int):
    quiz = get_object_or_404(Quiz.objects.select_related("course", "course__organization", "course__teacher"), pk=pk)
    if not _ensure_can_edit_quiz(request, quiz):
        return render(request, "403.html", status=403)

    data = _get_content_list(quiz)
    if not (0 <= qindex < len(data)):
        return render(request, "404.html", status=404)

    if request.method == "POST":
        del data[qindex]
        _save_content_list(quiz, data)
        messages.success(request, "Question deleted.")
        return redirect("quiz_questions", pk=quiz.pk)

    return render(
        request,
        "main_app/quiz_question_confirm_delete.html",
        {"quiz": quiz, "qindex": qindex, "question": data[qindex]},
    )


@login_required
def quiz_question_move(request, pk: int, qindex: int, direction: str):
    quiz = get_object_or_404(Quiz.objects.select_related("course", "course__organization", "course__teacher"), pk=pk)
    if not _ensure_can_edit_quiz(request, quiz):
        return render(request, "403.html", status=403)

    data = _get_content_list(quiz)
    if not (0 <= qindex < len(data)):
        return render(request, "404.html", status=404)

    if request.method == "POST":
        if direction == "up" and qindex > 0:
            data[qindex - 1], data[qindex] = data[qindex], data[qindex - 1]
        elif direction == "down" and qindex < len(data) - 1:
            data[qindex + 1], data[qindex] = data[qindex], data[qindex + 1]
        _save_content_list(quiz, data)
        return redirect("quiz_questions", pk=quiz.pk)

    return render(request, "403.html", status=403)


# --------------------
# Live Sessions
# --------------------
POINTS_PER_QUESTION = 10


def _quiz_questions(session: LiveSession):
    return _get_content_list(session.quiz)


def _get_idx_and_total(session: LiveSession):
    d = session.details or {}
    return int(d.get("current_index", -1)), int(d.get("total_questions", 0))


def _set_idx_and_total(session: LiveSession, idx: int, total: int):
    d = dict(session.details or {})
    d["current_index"] = idx
    d["total_questions"] = total
    session.details = d
    session.save(update_fields=["details"])


def _recompute_leaderboard(session: LiveSession):
    rows = []
    for p in LiveParticipant.objects.filter(livesession=session).only("id", "answer_questions", "user_id"):
        answers = p.answer_questions or []
        score = sum(int(a.get("points", 0)) for a in answers)
        rows.append((p, score))

    rows.sort(key=lambda t: t[1], reverse=True)

    LiveLeaderboard.objects.filter(livesession=session).delete()
    rank = 1
    for p, score in rows:
        LiveLeaderboard.objects.create(livesession=session, participant=p, rank=rank, score=score)
        rank += 1


def _evaluate(question: dict, selected_indexes: list[int]) -> int:
    qtype = (question.get("question_type") or "").upper()
    choices = question.get("choices") or []
    try:
        sel = {int(i) for i in selected_indexes}
    except Exception:
        sel = set()

    correct = {i for i, ch in enumerate(choices) if bool(ch.get("is_correct"))}

    if qtype == "MSQ":
        return POINTS_PER_QUESTION if (sel == correct) else 0

    if len(sel) != 1:
        return 0
    return POINTS_PER_QUESTION if (next(iter(sel)) in correct) else 0


@login_required
def livesession_create(request, quiz_id: int):
    quiz = get_object_or_404(Quiz.objects.select_related("course", "course__organization", "course__teacher"), pk=quiz_id)
    role, _ = _actor_role_and_org(request.user)

    if role != ROLE_SUPERUSER and not allowed(request.user, CREATE, LIVE_SESSION, org=quiz.course.organization):
        return render(request, "403.html", status=403)
    if role == ROLE_TEACHER and quiz.course.teacher_id != request.user.id:
        return render(request, "403.html", status=403)

    session = LiveSession.objects.create(
        quiz=quiz,
        host=request.user,
        details={"join_code": _short_code(), "lobby": []},
    )

    # Ensure join code exists (defensive)
    d = dict(session.details or {})
    if not d.get("join_code"):
        d["join_code"] = _short_code()
        session.details = d
        session.save(update_fields=["details"])

    # Realtime: show it on the course page immediately
    _course_group_send(quiz.course_id, {"op": "create", "session": _serialize_session_for_course(session)})

    messages.success(request, "Live session created.")
    return redirect("livesession_detail", pk=session.pk)


@login_required
def livesession_detail(request, pk: int):
    session = get_object_or_404(
        LiveSession.objects.select_related(
            "quiz", "quiz__course", "quiz__course__organization", "host"
        ),
        pk=pk,
    )
    role, _ = _actor_role_and_org(request.user)
    if role != ROLE_SUPERUSER and not allowed(
        request.user, READ_ONE, LIVE_SESSION, org=session.quiz.course.organization
    ):
        return render(request, "403.html", status=403)

    is_host = request.user.id == session.host_id
    questions = _quiz_questions(session)

    if request.method == "POST" and is_host:
        action = request.POST.get("action", "")

        if action == "regenerate_code" and not session.started_at and not session.ended_at:
            d = dict(session.details or {})
            d["join_code"] = _short_code()
            session.details = d
            session.save(update_fields=["details"])

            # Course page: update join code
            _course_group_send(session.quiz.course_id, {"op": "update", "session": _serialize_session_for_course(session)})

            messages.success(request, "Join code regenerated.")
            return redirect("livesession_detail", pk=session.pk)

        if action == "start" and session.started_at is None:
            session.started_at = timezone.now()
            lobby = list((session.details or {}).get("lobby", []))
            for uid in lobby:
                LiveParticipant.objects.get_or_create(livesession=session, user_id=uid)
            d = dict(session.details or {})
            d["lobby"] = []
            session.details = d
            session.save(update_fields=["started_at", "details"])
            _set_idx_and_total(session, idx=0 if questions else -1, total=len(questions))
            idx, total = _get_idx_and_total(session)

            # Live page: flip to started, clear lobby, refresh participants
            _live_update_send(session.id, {
                "started": True,
                "current_index": idx,
                "total": total,
                "lobby_users": [],
                "participants": _participants_rows_for_ws(session),
            })
            _live_event_send(session.id, {"kind": "started"})

            # Course page: update started_at column
            _course_group_send(session.quiz.course_id, {"op": "update", "session": _serialize_session_for_course(session)})

            return redirect("livesession_play", pk=session.pk)

        if action == "end" and session.ended_at is None:
            session.ended_at = timezone.now()
            session.save(update_fields=["ended_at"])
            _recompute_leaderboard(session)

            # Live page: ended + leaderboard
            _live_update_send(session.id, {"ended": True, "leaderboard": _leaderboard_rows_for_ws(session)})
            # Course page: remove from list
            _course_group_send(session.quiz.course_id, {"op": "remove", "session": {"id": session.id}})

            messages.success(request, "Session ended.")
            return redirect("livesession_detail", pk=session.pk)

        if action == "next" and session.started_at and not session.ended_at:
            idx, total = _get_idx_and_total(session)
            if 0 <= idx < total - 1:
                _set_idx_and_total(session, idx=idx + 1, total=total)
                # Live page: question changed
                _live_update_send(session.id, {"current_index": idx + 1, "total": total})
                _live_event_send(session.id, {"kind": "question_changed"})
                messages.success(request, "Next question.")
            else:
                session.ended_at = timezone.now()
                session.save(update_fields=["ended_at"])
                _recompute_leaderboard(session)

                _live_update_send(session.id, {"ended": True, "leaderboard": _leaderboard_rows_for_ws(session)})
                _course_group_send(session.quiz.course_id, {"op": "remove", "session": {"id": session.id}})

                messages.success(request, "No more questions. Session ended.")
            return redirect("livesession_detail", pk=session.pk)

        if action == "admit_user_id" and not session.started_at and not session.ended_at:
            try:
                uid = int(request.POST.get("user_id"))
            except (TypeError, ValueError):
                uid = None
            if uid:
                d = dict(session.details or {})
                lobby = set(d.get("lobby", []))
                if uid in lobby:
                    lobby.remove(uid)
                    d["lobby"] = list(lobby)
                    session.details = d
                    session.save(update_fields=["details"])
                LiveParticipant.objects.get_or_create(livesession=session, user_id=uid)

                # Live page: refresh lobby + participants
                _live_update_send(session.id, {
                    "lobby_users": _lobby_users_rows_for_ws(session),
                    "participants": _participants_rows_for_ws(session),
                })
                _live_event_send(session.id, {"kind": "admitted", "user_id": uid})

                messages.success(request, "Participant admitted.")
            return redirect("livesession_detail", pk=session.pk)

    lobby_ids = list((session.details or {}).get("lobby", []))
    lobby_users = list(User.objects.filter(id__in=lobby_ids).order_by("username"))
    participants = (
        LiveParticipant.objects.select_related("user")
        .filter(livesession=session)
        .order_by("user__username")
    )

    if session.ended_at:
        _recompute_leaderboard(session)
        leaderboard = (
            LiveLeaderboard.objects.select_related("participant", "participant__user")
            .filter(livesession=session)
            .order_by("rank")
        )
    else:
        temp = []
        for p in participants:
            score = sum(int(a.get("points", 0)) for a in (p.answer_questions or []))
            temp.append((p, score))
        temp.sort(key=lambda t: t[1], reverse=True)
        leaderboard = [{"rank": i + 1, "participant": p, "score": s} for i, (p, s) in enumerate(temp)]

    return render(
        request,
        "main_app/livesession_detail.html",
        {
            "session": session,
            "is_host": is_host,
            "lobby_users": lobby_users,
            "participants": participants,
            "leaderboard": leaderboard,
        },
    )


@login_required
def livesession_play(request, pk: int):
    session = get_object_or_404(
        LiveSession.objects.select_related("quiz", "quiz__course", "quiz__course__organization", "host"), pk=pk
    )
    role, _ = _actor_role_and_org(request.user)

    if role != ROLE_SUPERUSER and not allowed(request.user, READ_ONE, LIVE_SESSION, org=session.quiz.course.organization):
        return render(request, "403.html", status=403)

    questions = _quiz_questions(session)
    idx, total = _get_idx_and_total(session)
    is_host = request.user.id == session.host_id

    if session.started_at is None and session.ended_at is None:
        return render(request, "main_app/play.html", {"session": session, "state": "waiting", "is_host": is_host})

    if session.ended_at is not None:
        _recompute_leaderboard(session)
        board = (
            LiveLeaderboard.objects.select_related("participant", "participant__user")
            .filter(livesession=session)
            .order_by("rank")
        )
        return render(
            request,
            "main_app/play.html",
            {"session": session, "state": "ended", "leaderboard": board, "is_host": is_host},
        )

    if not (0 <= idx < total):
        session.ended_at = timezone.now()
        session.save(update_fields=["ended_at"])
        _recompute_leaderboard(session)
        board = (
            LiveLeaderboard.objects.select_related("participant", "participant__user")
            .filter(livesession=session)
            .order_by("rank")
        )
        return render(
            request,
            "main_app/play.html",
            {"session": session, "state": "ended", "leaderboard": board, "is_host": is_host},
        )

    question = questions[idx]

    if not is_host:
        lp, _ = LiveParticipant.objects.get_or_create(livesession=session, user=request.user)
    else:
        lp = None

    if request.method == "POST":
        action = request.POST.get("action")

        if is_host and action == "next":
            if idx < total - 1:
                _set_idx_and_total(session, idx=idx + 1, total=total)
                # Live WS: everyone advances without refresh
                _live_update_send(session.id, {"current_index": idx + 1, "total": total})
                _live_event_send(session.id, {"kind": "question_changed"})
                messages.success(request, "Next question.")
            else:
                session.ended_at = timezone.now()
                session.save(update_fields=["ended_at"])
                _recompute_leaderboard(session)

                # Live WS + Course WS
                _live_update_send(session.id, {"ended": True, "leaderboard": _leaderboard_rows_for_ws(session)})
                _course_group_send(session.quiz.course_id, {"op": "remove", "session": {"id": session.id}})

                messages.success(request, "Session ended.")
            return redirect("livesession_play", pk=session.pk)

        if action == "answer" and lp:
            answers = list(lp.answer_questions or [])
            already = any(int(a.get("question_id", -999)) == idx for a in answers)
            if not already:
                selected_raw = request.POST.getlist("choice")
                try:
                    sel_ints = [int(s) for s in selected_raw]
                except Exception:
                    sel_ints = []
                points = _evaluate(question, sel_ints)
                answers.append({"question_id": idx, "points": points, "selected": sel_ints})
                lp.answer_questions = answers
                lp.save(update_fields=["answer_questions"])
                messages.success(request, "Answer submitted.")
            return redirect("livesession_play", pk=session.pk)

    already_answered = False
    selected = set()

    if lp:
        answers = lp.answer_questions or []
        for a in answers:
            try:
                if int(a.get("question_id", -999)) == idx:
                    already_answered = True
                    selected = {int(i) for i in (a.get("selected") or [])}
                    break
            except (TypeError, ValueError):
                pass

    return render(
        request,
        "main_app/play.html",
        {
            "session": session,
            "is_host": is_host,
            "state": "playing",
            "idx": idx,
            "total": total,
            "question": question,
            "already_answered": already_answered,
            "selected": selected,
        },
    )


@login_required
def livesession_join(request):
    if request.method == "POST":
        code = (request.POST.get("join_code") or "").strip().upper()
        session = LiveSession.objects.filter(details__join_code=code).select_related(
            "quiz", "quiz__course", "quiz__course__organization"
        ).first()
        if not session:
            return render(request, "main_app/join.html", {"error": "Invalid join code."})

        role, org = _actor_role_and_org(request.user)
        if role not in {ROLE_STUDENT, ROLE_TEACHER, ROLE_PARENTS, ROLE_ADMIN, ROLE_MANAGER, ROLE_SUPERUSER}:
            return render(request, "403.html", status=403)
        if role != ROLE_SUPERUSER and org and org.id != session.quiz.course.organization_id:
            return render(request, "403.html", status=403)

        if session.started_at and not session.ended_at:
            LiveParticipant.objects.get_or_create(livesession=session, user=request.user)
            return redirect("livesession_play", pk=session.pk)

        d = dict(session.details or {})
        lobby = set(d.get("lobby", []))
        lobby.add(request.user.id)
        d["lobby"] = list(lobby)
        session.details = d
        session.save(update_fields=["details"])

        # NEW: push lobby → all connected clients (host sees lobby update instantly)
        _live_update_send(session.id, {"lobby_users": _lobby_users_rows_for_ws(session)})

        return render(request, "main_app/join.html", {"session": session, "waiting": True})

    return render(request, "main_app/join.html")


@login_required
def livesession_status(request, pk: int):
    session = get_object_or_404(
        LiveSession.objects.select_related("quiz", "quiz__course", "quiz__course__organization"),
        pk=pk,
    )
    role, _ = _actor_role_and_org(request.user)
    if role != ROLE_SUPERUSER and not allowed(request.user, READ_ONE, LIVE_SESSION, org=session.quiz.course.organization):
        return JsonResponse({"error": "forbidden"}, status=403)

    idx, total = _get_idx_and_total(session)
    return JsonResponse(
        {
            "started": bool(session.started_at),
            "ended": bool(session.ended_at),
            "current_index": idx,
            "total": total,
        }
    )

@login_required
def livesession_answers(request, pk: int):
    # Load session + permission gate
    session = get_object_or_404(
        LiveSession.objects.select_related(
            "quiz", "quiz__course", "quiz__course__organization", "host"
        ),
        pk=pk,
    )
    role, _org = _actor_role_and_org(request.user)

    # Must have org-scoped read on the session
    if role != ROLE_SUPERUSER and not allowed(
        request.user, READ_ONE, LIVE_SESSION, org=session.quiz.course.organization
    ):
        return render(request, "403.html", status=403)

    # Who’s allowed to view detailed answers?
    # - Superuser/Admin/Manager
    # - Teacher, but only if they own this course (host)
    if role == ROLE_TEACHER and request.user.id != session.host_id:
        return render(request, "403.html", status=403)
    if role in {ROLE_STUDENT, ROLE_PARENTS}:
        return render(request, "403.html", status=403)

    if not session.ended_at:
        messages.info(request, "This session hasn’t ended yet.")
        return redirect("livesession_detail", pk=session.pk)

    # Build per-question rows
    questions = _quiz_questions(session)  # uses your existing helper
    participants = list(
        LiveParticipant.objects.select_related("user")
        .filter(livesession=session)
        .order_by("user__username")
    )

    per_question = []
    for idx, q in enumerate(questions):
        q_rows = []
        for p in participants:
            # find participant's answer for this question index
            ans = None
            for a in (p.answer_questions or []):
                try:
                    if int(a.get("question_id", -999)) == idx:
                        ans = a
                        break
                except (TypeError, ValueError):
                    pass

            if ans:
                selected = []
                for raw in (ans.get("selected") or []):
                    try:
                        selected.append(int(raw))
                    except Exception:
                        continue
                # Map selected indexes → choice text
                choice_texts = []
                for i in selected:
                    chs = q.get("choices") or []
                    if 0 <= i < len(chs):
                        choice_texts.append(chs[i].get("text") or f"Choice {i+1}")
                points = int(ans.get("points", 0))
                q_rows.append(
                    {
                        "user": p.user,
                        "selected_indexes": selected,
                        "selected_texts": choice_texts,
                        "points": points,
                        "skipped": False,
                    }
                )
            else:
                q_rows.append(
                    {
                        "user": p.user,
                        "selected_indexes": [],
                        "selected_texts": [],
                        "points": 0,
                        "skipped": True,
                    }
                )

        # stats
        attempted = sum(1 for r in q_rows if not r["skipped"])
        correct = sum(1 for r in q_rows if r["points"] > 0)
        avg_points = round(sum(r["points"] for r in q_rows) / max(len(q_rows), 1), 2)

        per_question.append(
            {
                "index": idx,
                "question": q,
                "rows": q_rows,
                "stats": {"attempted": attempted, "correct": correct, "avg_points": avg_points},
            }
        )

    return render(
        request,
        "main_app/livesession_answers.html",
        {
            "session": session,
            "per_question": per_question,
        },
    )

