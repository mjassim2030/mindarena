# main_app/consumers.py
from __future__ import annotations

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import F

from .models import (
    LiveSession, LiveParticipant, LiveLeaderboard, OrgMembership, Course
)
from .constants import (
    ROLE_SUPERUSER, ROLE_ADMIN, ROLE_MANAGER, ROLE_TEACHER, ROLE_STUDENT, ROLE_PARENTS
)
from .permissions import allowed, READ_ONE, COURSE as COURSE_RES, LIVE_SESSION
from .views import _get_idx_and_total, _set_idx_and_total  # reuse helpers

User = get_user_model()

# ----------------------- Small serializer & broadcast helper -----------------------

def _serialize_session_for_course(session: LiveSession) -> dict:
    d = dict(session.details or {})
    return {
        "id": session.id,
        "quiz_title": session.quiz.quiz_title,
        "host_name": session.host.get_full_name() or session.host.username,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "join_code": d.get("join_code"),
    }

def broadcast_course_session(session: LiveSession, op: str) -> None:
    """
    Use this from *views* to notify the course page:
      - op="create"   after creating a LiveSession
      - op="update"   after regenerating code / starting the session
      - op="remove"   after ending/deleting a session
    """
    payload = {"op": op}
    if op == "remove":
        payload["session"] = {"id": session.id}
    else:
        payload["session"] = _serialize_session_for_course(session)
    async_to_sync(get_channel_layer().group_send)(
        f"course_{session.quiz.course_id}",
        {"type": "course.update", "payload": payload},
    )

# ----------------------- Pure sync helpers -----------------------

def _questions(session: LiveSession):
    """Normalize quiz questions shape from session.quiz.content."""
    content = session.quiz.content or []
    out = []
    for d in content:
        out.append({
            "question": d.get("question") or d.get("Question") or "",
            "question_type": (d.get("question_type") or d.get("QuestionType") or "MCQ").upper(),
            "image": d.get("image"),
            "choices": d.get("choices") or d.get("Choices") or [],
        })
    return out

def _evaluate(question: dict, selected_indexes):
    """Return points for a selection according to question type (MCQ/MSQ)."""
    try:
        sel = {int(i) for i in selected_indexes}
    except Exception:
        sel = set()
    correct = {i for i, ch in enumerate(question.get("choices") or []) if bool(ch.get("is_correct"))}
    qtype = (question.get("question_type") or "").upper()
    if qtype == "MSQ":
        return 10 if sel == correct else 0
    if len(sel) != 1:
        return 0
    return 10 if next(iter(sel)) in correct else 0

# ----------------------- DB helpers (wrapped) -----------------------

@database_sync_to_async
def _get_course(course_id: int):
    return Course.objects.select_related("organization", "teacher").filter(pk=course_id).first()

@database_sync_to_async
def _get_session(pk: int) -> LiveSession | None:
    return (
        LiveSession.objects
        .select_related("quiz", "quiz__course", "quiz__course__organization", "host")
        .filter(pk=pk)
        .first()
    )

@database_sync_to_async
def _actor_role_org(user):
    mem = OrgMembership.objects.select_related("organization").filter(user=user).first()
    if not mem:
        return None, None
    return mem.role, mem.organization

@database_sync_to_async
def _can_view_course(user, course: Course) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not allowed(user, READ_ONE, COURSE_RES, org=course.organization):
        return False
    mem = OrgMembership.objects.select_related("organization").filter(user=user).first()
    role = mem.role if mem else None
    if role in {ROLE_ADMIN, ROLE_MANAGER}:
        return True
    if role == ROLE_TEACHER:
        return course.teacher_id == user.id
    if role in {ROLE_STUDENT, ROLE_PARENTS}:
        return user.id in (course.enrolled_students or [])
    return False

@database_sync_to_async
def _ongoing_sessions_rows(course: Course):
    # Created or started but not ended
    qs = (
        LiveSession.objects
        .select_related("quiz", "host")
        .filter(quiz__course=course, ended_at__isnull=True)
        .order_by("-started_at", "-id")
    )
    return [_serialize_session_for_course(s) for s in qs]

@database_sync_to_async
def _can_read_session(user, session: LiveSession) -> bool:
    if user.is_authenticated and user.is_superuser:
        return True
    mem = OrgMembership.objects.select_related("organization").filter(user=user).first()
    if not mem:
        return False
    return allowed(user, READ_ONE, LIVE_SESSION, org=session.quiz.course.organization)

@database_sync_to_async
def _lobby_users_rows(session: LiveSession):
    lobby_ids = list((session.details or {}).get("lobby", []))
    if not lobby_ids:
        return []
    by_id = {
        u["id"]: u
        for u in User.objects.filter(id__in=lobby_ids).values(
            "id", "username", "first_name", "last_name", "email"
        )
    }
    return [by_id[i] for i in lobby_ids if i in by_id]

@database_sync_to_async
def _participants_rows(session: LiveSession):
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

@database_sync_to_async
def _add_to_lobby(session: LiveSession, user_id: int):
    d = dict(session.details or {})
    lobby = set(d.get("lobby", []))
    lobby.add(user_id)
    d["lobby"] = list(lobby)
    session.details = d
    session.save(update_fields=["details"])
    return d["lobby"]

@database_sync_to_async
def _admit_user(session: LiveSession, user_id: int):
    d = dict(session.details or {})
    lobby = set(d.get("lobby", []))
    if user_id in lobby:
        lobby.remove(user_id)
        d["lobby"] = list(lobby)
        session.details = d
        session.save(update_fields=["details"])
    LiveParticipant.objects.get_or_create(livesession=session, user_id=user_id)
    return list(lobby)

@database_sync_to_async
def _start_session(session: LiveSession):
    if session.started_at:
        return _get_idx_and_total(session)
    session.started_at = timezone.now()
    lobby = list((session.details or {}).get("lobby", []))
    for uid in lobby:
        LiveParticipant.objects.get_or_create(livesession=session, user_id=uid)
    d = dict(session.details or {})
    d["lobby"] = []
    session.details = d
    session.save(update_fields=["started_at", "details"])
    qs = _questions(session)
    _set_idx_and_total(session, idx=0 if qs else -1, total=len(qs))
    return _get_idx_and_total(session)

@database_sync_to_async
def _next_or_end(session: LiveSession):
    idx, total = _get_idx_and_total(session)
    if 0 <= idx < total - 1:
        _set_idx_and_total(session, idx=idx + 1, total=total)
        return "next", idx + 1, total, None
    # End
    session.ended_at = timezone.now()
    session.save(update_fields=["ended_at"])
    _recompute_leaderboard_sync(session)
    rows = list(
        LiveLeaderboard.objects.select_related("participant", "participant__user")
        .filter(livesession=session).order_by("rank")
        .values(
            "rank", "score",
            username=F("participant__user__username"),
            first_name=F("participant__user__first_name"),
            last_name=F("participant__user__last_name"),
        )
    )
    return "ended", -1, total, rows

@database_sync_to_async
def _end_session(session: LiveSession):
    if not session.ended_at:
        session.ended_at = timezone.now()
        session.save(update_fields=["ended_at"])
        _recompute_leaderboard_sync(session)
    rows = list(
        LiveLeaderboard.objects.select_related("participant", "participant__user")
        .filter(livesession=session).order_by("rank")
        .values(
            "rank", "score",
            username=F("participant__user__username"),
            first_name=F("participant__user__first_name"),
            last_name=F("participant__user__last_name"),
        )
    )
    return rows

def _recompute_leaderboard_sync(session: LiveSession):
    rows = []
    for p in LiveParticipant.objects.filter(livesession=session).only("id", "answer_questions", "user_id"):
        answers = p.answer_questions or []
        score = sum(int(a.get("points", 0)) for a in answers)
        rows.append((p, score))
    rows.sort(key=lambda t: t[1], reverse=True)
    LiveLeaderboard.objects.filter(livesession=session).delete()
    for rank, (p, score) in enumerate(rows, start=1):
        LiveLeaderboard.objects.create(livesession=session, participant=p, rank=rank, score=score)

@database_sync_to_async
def _submit_answer(session: LiveSession, user_id: int, selected):
    lp, _ = LiveParticipant.objects.get_or_create(livesession=session, user_id=user_id)
    idx, total = _get_idx_and_total(session)
    if not (0 <= idx < total):
        return {"ended": True}
    qs = _questions(session)
    q = qs[idx]
    answers = list(lp.answer_questions or [])
    if any(int(a.get("question_id", -999)) == idx for a in answers):
        return {"already": True}
    points = _evaluate(q, selected or [])
    answers.append({"question_id": idx, "points": points, "selected": [int(i) for i in (selected or [])]})
    lp.answer_questions = answers
    lp.save(update_fields=["answer_questions"])
    return {"ok": True, "points": points}

# ----------------------- Consumers -----------------------

class CourseSessionsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.course_id = int(self.scope["url_route"]["kwargs"]["course_id"])
        self.group_name = f"course_{self.course_id}"

        self.course = await _get_course(self.course_id)
        if not self.course or not await _can_view_course(self.scope["user"], self.course):
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Initial list (created or started, but not ended)
        sessions = await _ongoing_sessions_rows(self.course)
        await self.send_json({"type": "snapshot", "sessions": sessions})

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Group push → client
    async def course_update(self, event):
        # payload: {"op": "create"|"update"|"remove", "session": {...}}
        await self.send_json({"type": "update", **event["payload"]})

class LiveSessionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = int(self.scope["url_route"]["kwargs"]["pk"])
        self.group_name = f"live_{self.session_id}"
        self.session = await _get_session(self.session_id)

        user = self.scope.get("user")
        if not self.session or not user or not user.is_authenticated:
            await self.close()
            return

        role, _org = await _actor_role_org(user)
        if role != ROLE_SUPERUSER:
            can = await _can_read_session(user, self.session)
            if not can:
                await self.close()
                return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        idx, total = _get_idx_and_total(self.session)
        lobby_users = await _lobby_users_rows(self.session)
        participants = await _participants_rows(self.session)

        await self.send_json({
            "type": "snapshot",
            "is_host": user.id == self.session.host_id,
            "started": bool(self.session.started_at),
            "ended": bool(self.session.ended_at),
            "current_index": idx,
            "total": total,
            "lobby_users": lobby_users,
            "participants": participants,
        })

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        user = self.scope["user"]
        action = (content or {}).get("action")
        if not action:
            return

        # Student joins lobby
        if action == "join_lobby":
            await _add_to_lobby(self.session, user.id)
            lobby_users = await _lobby_users_rows(self.session)
            await self.channel_layer.group_send(self.group_name, {
                "type": "session.update",
                "payload": {"lobby_users": lobby_users},
            })
            return

        # Host actions
        is_host = (user.id == self.session.host_id)

        if action == "admit" and is_host:
            uid = int(content.get("user_id") or 0)
            await _admit_user(self.session, uid)
            lobby_users = await _lobby_users_rows(self.session)
            participants = await _participants_rows(self.session)
            await self.channel_layer.group_send(self.group_name, {
                "type": "session.update",
                "payload": {"lobby_users": lobby_users, "participants": participants},
            })
            await self.channel_layer.group_send(self.group_name, {
                "type": "session.event",
                "payload": {"kind": "admitted", "user_id": uid},
            })
            return

        if action == "start" and is_host:
            idx, total = await _start_session(self.session)
            participants = await _participants_rows(self.session)

            # Update Live page
            await self.channel_layer.group_send(self.group_name, {
                "type": "session.update",
                "payload": {
                    "started": True,
                    "current_index": idx,
                    "total": total,
                    "lobby_users": [],
                    "participants": participants,
                },
            })
            await self.channel_layer.group_send(self.group_name, {
                "type": "session.event",
                "payload": {"kind": "started"},
            })

            # Update Course page (started_at column)
            await self.channel_layer.group_send(
                f"course_{self.session.quiz.course_id}",
                {"type": "course.update",
                 "payload": {"op": "update", "session": _serialize_session_for_course(self.session)}},
            )
            return

        if action == "next" and is_host:
            status, idx, total, rows = await _next_or_end(self.session)
            if status == "next":
                await self.channel_layer.group_send(self.group_name, {
                    "type": "session.update",
                    "payload": {"current_index": idx, "total": total},
                })
                await self.channel_layer.group_send(self.group_name, {
                    "type": "session.event",
                    "payload": {"kind": "question_changed"},
                })
            else:
                # Ended
                await self.channel_layer.group_send(self.group_name, {
                    "type": "session.update",
                    "payload": {"ended": True, "leaderboard": rows},
                })
                await self.channel_layer.group_send(
                    f"course_{self.session.quiz.course_id}",
                    {"type": "course.update", "payload": {"op": "remove", "session": {"id": self.session.id}}},
                )
            return

        if action == "end" and is_host:
            rows = await _end_session(self.session)
            await self.channel_layer.group_send(self.group_name, {
                "type": "session.update",
                "payload": {"ended": True, "leaderboard": rows},
            })
            await self.channel_layer.group_send(
                f"course_{self.session.quiz.course_id}",
                {"type": "course.update", "payload": {"op": "remove", "session": {"id": self.session.id}}},
            )
            return

        if action == "answer":
            selected = content.get("selected") or []
            res = await _submit_answer(self.session, user.id, selected)
            await self.send_json({"type": "answer_ack", **(res or {})})
            return

    # Group → socket
    async def session_update(self, event):
        await self.send_json({"type": "update", **event["payload"]})

    async def session_event(self, event):
        await self.send_json({"type": "event", **event["payload"]})
