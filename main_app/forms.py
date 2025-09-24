from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.forms import formset_factory

from .constants import (
    ROLE_CHOICES,
    ROLE_SUPERUSER,
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_TEACHER,
)
from .models import Organization, OrgMembership, Course

User = get_user_model()

ROLE_LIMIT = {"manager", "teacher", "student", "parents"}
ROLE_CHOICES_LIMITED = tuple((v, l) for v, l in ROLE_CHOICES if v in ROLE_LIMIT)

QTYPES = (
    ("MCQ", "Multiple choice (one correct)"),
    ("MSQ", "Multiple select (many correct)"),
    ("TF", "True/False"),
)


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.order_by("name"),
        required=True,
        label="Organization",
        empty_label="— Select organization —",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")


class JoinOrganizationForm(UserCreationForm):
    org_name = forms.CharField(label="Organization name", max_length=255)
    country = forms.CharField(label="Country", max_length=64)
    email = forms.EmailField(label="Email", required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def create_organization(self) -> Organization:
        return Organization.objects.create(
            name=self.cleaned_data["org_name"],
            country=self.cleaned_data["country"],
        )


class OrgMemberCreateForm(forms.Form):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.order_by("name"),
        required=False,
        label="Organization",
        empty_label="— Select organization —",
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES_LIMITED, label="Role")
    username = forms.CharField(max_length=150, label="Username")
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput, required=False)


class OrgMemberEditForm(forms.Form):
    role = forms.ChoiceField(choices=ROLE_CHOICES_LIMITED, label="Role")
    username = forms.CharField(max_length=150, label="Username")
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="New Password", widget=forms.PasswordInput, required=False)

    def initialize_from_membership(self, membership: OrgMembership):
        u = membership.user
        self.initial.update(
            {
                "role": membership.role,
                "username": u.username,
                "email": u.email,
            }
        )


class CourseJoinForm(forms.Form):
    join_code = forms.CharField(max_length=32, label="Join Code")


class CourseCreateForm(forms.Form):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.order_by("name"),
        required=False,
        label="Organization",
        empty_label="— Select organization —",
    )
    teacher = forms.ModelChoiceField(queryset=User.objects.none(), label="Teacher")
    course_name = forms.CharField(max_length=255, label="Course name")
    join_code = forms.CharField(max_length=32, label="Join code")
    subject_category = forms.ChoiceField(
        choices=Course._meta.get_field("subject_category").choices, label="Subject"
    )

    def __init__(self, *args, actor_role=None, actor_org=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor_role = actor_role
        self.actor_org = actor_org

        if actor_role in {ROLE_ADMIN, ROLE_MANAGER} and actor_org:
            self.fields["organization"].required = False
            self.fields["organization"].widget = forms.HiddenInput()
            self.initial["organization"] = actor_org.pk
            teacher_ids = (
                OrgMembership.objects.filter(organization=actor_org, role=ROLE_TEACHER)
                .values_list("user_id", flat=True)
            )
            self.fields["teacher"].queryset = User.objects.filter(id__in=teacher_ids).order_by("username")
        else:
            teacher_ids = OrgMembership.objects.filter(role=ROLE_TEACHER).values_list("user_id", flat=True)
            self.fields["teacher"].queryset = User.objects.filter(id__in=teacher_ids).order_by("username")

    def cleaned_org(self) -> Organization:
        if self.actor_role in {ROLE_ADMIN, ROLE_MANAGER} and self.actor_org:
            return self.actor_org
        org = self.cleaned_data.get("organization")
        if not org:
            raise forms.ValidationError("Organization is required.")
        return org

    def cleaned_teacher(self, org: Organization) -> User:
        teacher: User = self.cleaned_data["teacher"]
        exists = OrgMembership.objects.filter(organization=org, user=teacher, role=ROLE_TEACHER).exists()
        if not exists:
            raise forms.ValidationError("Selected teacher is not part of the chosen organization.")
        return teacher


class QuizCreateForm(forms.Form):
    course = forms.ModelChoiceField(queryset=Course.objects.none(), label="Course")
    quiz_title = forms.CharField(max_length=255, label="Quiz title")

    def __init__(self, *args, actor_role=None, actor_org=None, actor_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor_role = actor_role
        self.actor_org = actor_org
        self.actor_user = actor_user

        if actor_role == ROLE_SUPERUSER:
            qs = Course.objects.select_related("organization", "teacher").order_by("course_name")
        elif actor_role in {ROLE_ADMIN, ROLE_MANAGER} and actor_org:
            qs = Course.objects.filter(organization=actor_org).select_related("teacher").order_by("course_name")
        elif actor_role == ROLE_TEACHER and actor_org:
            qs = Course.objects.filter(organization=actor_org, teacher=actor_user).order_by("course_name")
        else:
            qs = Course.objects.none()

        self.fields["course"].queryset = qs


class QuizEditForm(QuizCreateForm):
    def __init__(self, *args, actor_role=None, actor_org=None, actor_user=None, instance=None, **kwargs):
        super().__init__(*args, actor_role=actor_role, actor_org=actor_org, actor_user=actor_user, **kwargs)
        if instance:
            self.initial["course"] = instance.course_id
            self.initial["quiz_title"] = instance.quiz_title
        self.instance = instance
        

class QuestionForm(forms.Form):
    question_type = forms.ChoiceField(
        choices=(("MCQ", "Multiple choice"), ("MSQ", "Multiple select"), ("TF", "True/False")),
        label="Type",
        widget=forms.HiddenInput  # we’ll control it with pretty buttons in the template
    )
    image = forms.ImageField(required=False, label="Upload image")
    question = forms.CharField(max_length=1000, label="Question", widget=forms.Textarea(attrs={"rows": 3}))
    correct_tf = forms.ChoiceField(
        choices=(("T", "True"), ("F", "False")),
        widget=forms.RadioSelect, required=False, label="Correct answer (TF)"
    )

class ChoiceForm(forms.Form):
    text = forms.CharField(max_length=255, label="Choice")
    is_correct = forms.BooleanField(required=False, label="Correct")


ChoiceFormSet = formset_factory(ChoiceForm, extra=2, can_delete=True)
