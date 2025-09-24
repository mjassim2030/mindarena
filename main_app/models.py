from django.db import models
from django.conf import settings
from .constants import ROLE_CHOICES, DEFAULT_ROLE, SUBJECT_CATEGORIES
import secrets
import string

QUESTION_TYPES = (
    ('MCQ', 'Multiple Choice'),
    ('MSQ', 'Multiple Select'),
    ('TF', 'True/False'),
    ('NUMERIC', 'Numeric'),
    ('TEXT', 'Short Text'),
    ('ORDER', 'Ordering'),
    ('MATCH', 'Matching'),
    ('IMAGE_HOTSPOT', 'Image Hotspot'),
)

class Organization(models.Model):
    name = models.CharField("Organization name", max_length=255, unique=True)
    country = models.CharField("Country (ISO-3166 alpha-2 or name)", max_length=64)
    logo_url = models.URLField("Logo URL", blank=True)
    website_url = models.URLField("Website URL", blank=True)
    linkedin_url = models.URLField("LinkedIn URL", blank=True)
    twitter_url = models.URLField("Twitter/X URL", blank=True)
    facebook_url = models.URLField("Facebook URL", blank=True)
    instagram_url = models.URLField("Instagram URL", blank=True)
    youtube_url = models.URLField("YouTube URL", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class OrgMembership(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="org_memberships",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=DEFAULT_ROLE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "user")
        indexes = [
            models.Index(fields=["organization", "user"]),
            models.Index(fields=["role"]),
        ]
        ordering = ["organization_id", "user_id"]

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization} ({self.get_role_display()})"


class Course(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="courses")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="teaching_courses")
    course_name = models.CharField(max_length=255)
    join_code = models.CharField(max_length=32, unique=True)
    subject_category = models.CharField(max_length=32, choices=SUBJECT_CATEGORIES)
    enrolled_students = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["course_name"]
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["teacher"]),
            models.Index(fields=["join_code"]),
        ]

    def __str__(self):
        return f"{self.course_name} ({self.organization.name})"


def default_quiz_content():
    return []


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="quizzes")
    quiz_title = models.CharField(max_length=255)
    content = models.JSONField(default=default_quiz_content, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["quiz_title"]
        indexes = [
            models.Index(fields=["course"]),
            models.Index(fields=["quiz_title"]),
        ]

    def __str__(self) -> str:
        return f"{self.quiz_title} — {self.course.course_name}"


def _short_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def default_session_details():
    return {"join_code": _short_code(), "lobby": []}


def default_answers():
    return []


class LiveSession(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="live_sessions")
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="hosted_sessions")
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    details = models.JSONField(default=default_session_details, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["quiz"]),
            models.Index(fields=["host"]),
            models.Index(fields=["started_at"]),
            models.Index(fields=["ended_at"]),
        ]

    def __str__(self) -> str:
        return f"LiveSession #{self.pk} — {self.quiz.quiz_title}"

    @property
    def join_code(self) -> str:
        return (self.details or {}).get("join_code", "")

    def regenerate_join_code(self, length=6, save=True):
        d = dict(self.details or {})
        d["join_code"] = _short_code(length)
        self.details = d
        if save:
            self.save(update_fields=["details"])


class LiveParticipant(models.Model):
    livesession = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_participations")
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    answer_questions = models.JSONField(default=default_answers, blank=True)

    class Meta:
        unique_together = ("livesession", "user")
        indexes = [
            models.Index(fields=["livesession"]),
            models.Index(fields=["user"]),
        ]
        ordering = ["livesession_id", "user_id"]

    def __str__(self) -> str:
        return f"{self.user} in session {self.livesession_id}"


class LiveLeaderboard(models.Model):
    livesession = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="leaderboard_entries")
    participant = models.OneToOneField(LiveParticipant, on_delete=models.CASCADE, related_name="leaderboard_row")
    rank = models.PositiveIntegerField(default=0)
    score = models.IntegerField(default=0)

    class Meta:
        unique_together = ("livesession", "participant")
        indexes = [
            models.Index(fields=["livesession", "rank"]),
            models.Index(fields=["livesession", "score"]),
        ]
        ordering = ["livesession_id", "rank"]

    def __str__(self) -> str:
        return f"Rank {self.rank} — {self.participant}"
