from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q

#  Choices Enums
ROLES = (
    ('TEACHER','Teacher'),
    ('STUDENT','Student'),
    ('PARENT','Parent'),
    ('PARTNER','Partner'),
    ('ADMIN','Admin'),
)

ORG_ROLES = (
    ('OWNER','Owner'),
    ('ADMIN','Admin'),
    ('TEACHER','Teacher'),
    ('STUDENT','Student'),
)

QUESTION_TYPES = (
    ('MCQ','Multiple Choice'),
    ('MSQ','Multiple Select'),
    ('TF','True/False'),
    ('NUMERIC','Numeric'),
    ('TEXT','Short Text'),
    ('ORDER','Ordering'),
    ('MATCH','Matching'),
    ('IMAGE_HOTSPOT','Image Hotspot'),
)

ATTEMPT_STATUSES = (
    ('IN_PROGRESS','In progress'),
    ('SUBMITTED','Submitted'),
    ('GRADED','Graded'),
)

LIVE_MODES = (
    ('CLASSIC','Classic'),
    ('TEAM','Team'),
    ('POWERUPS','Power-ups'),
)

LIVE_EVENT_TYPES = (
    ('JOIN','Join'),
    ('START','Start'),
    ('QUESTION','Question'),
    ('ANSWER','Answer'),
    ('SCORE','Score'),
    ('LEADERBOARD','Leaderboard'),
    ('END','End'),
)

LISTING_STATUSES = (
    ('ACTIVE','Active'),
    ('PAUSED','Paused'),
    ('RETIRED','Retired'),
)

PAYOUT_STATUSES = (
    ('PENDING','Pending'),
    ('PAID','Paid'),
    ('FAILED','Failed'),
)

# ---------- Orgs ----------

class Organization(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name


class OrgMembership(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    org_role = models.CharField(max_length=12, choices=ORG_ROLES, default=ORG_ROLES[3][0])

    class Meta:
        unique_together = ("org","user")


# ---------- Courses & Enrollment ----------

class Course(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.PROTECT)
    name = models.TextField()
    join_code = models.CharField(max_length=6, unique=True)

    def __str__(self):
        return f"{self.name} ({self.join_code})"


class CourseMember(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("course","user")


# ---------- Quizzes & Content ----------

class Quiz(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.TextField()
    description = models.TextField(default="", blank=True)
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class QuizVersion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    version_no = models.IntegerField()
    notes = models.TextField(default="", blank=True)

    class Meta:
        unique_together = ("quiz","version_no")


class Question(models.Model):
    quiz_version = models.ForeignKey(QuizVersion, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    prompt = models.TextField()
    meta = models.JSONField(default=dict, blank=True)
    order_index = models.IntegerField(default=0)


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    label = models.TextField()
    is_correct = models.BooleanField(default=False)
    order_index = models.IntegerField(default=0)


class QuestionMedia(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    kind = models.CharField(max_length=16, choices=[('IMAGE','Image'),('AUDIO','Audio'),('VIDEO','Video')])
    url = models.TextField()
    attrib = models.JSONField(default=dict, blank=True)


class ChoiceMedia(models.Model):
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    kind = models.CharField(max_length=16, choices=[('IMAGE','Image'),('AUDIO','Audio'),('VIDEO','Video')])
    url = models.TextField()


class Tag(models.Model):
    name = models.TextField(unique=True)

    def __str__(self):
        return self.name


class QuizTag(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("quiz","tag")


# ---------- Assignments & Attempts ----------

class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT)
    open_at = models.DateTimeField()
    due_at = models.DateTimeField(null=True, blank=True)
    settings = models.JSONField(default=dict, blank=True)

class Attempt(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=ATTEMPT_STATUSES, default='IN_PROGRESS')

    class Meta:
        indexes = [
            models.Index(fields=("assignment","user")),
        ]


class AttemptItem(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.RESTRICT)
    answer_payload = models.JSONField()
    time_taken_ms = models.IntegerField(default=0)
    is_correct = models.BooleanField()
    points_awarded = models.IntegerField(default=0)
    order_index = models.IntegerField(default=0)


class AttemptScore(models.Model):
    attempt = models.OneToOneField(Attempt, on_delete=models.CASCADE)
    total_points = models.IntegerField()
    max_points = models.IntegerField()
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    breakdown = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(percent__gte=0) & Q(percent__lte=100), name="attempt_score_percent_0_100"),
        ]


# ---------- Live Sessions ----------

class LiveSession(models.Model):
    quiz_version = models.ForeignKey(QuizVersion, on_delete=models.PROTECT)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    mode = models.CharField(max_length=12, choices=LIVE_MODES, default='CLASSIC')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    settings = models.JSONField(default=dict, blank=True)


class LiveParticipant(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nickname = models.TextField()
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("session","nickname")


class LiveEvent(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE)
    type = models.CharField(max_length=16, choices=LIVE_EVENT_TYPES)
    ts = models.DateTimeField(default=timezone.now)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("session","ts")),
        ]


class LiveLeaderboard(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE)
    participant = models.ForeignKey(LiveParticipant, on_delete=models.CASCADE)
    rank = models.IntegerField()
    score = models.IntegerField()
    streak = models.IntegerField(default=0)


# ---------- Gamification ----------

class XPTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    delta = models.IntegerField()
    reason = models.TextField()
    related_id = models.CharField(max_length=64, null=True, blank=True)


class Badge(models.Model):
    code = models.TextField(unique=True)
    name = models.TextField()
    description = models.TextField(default="", blank=True)
    icon_url = models.TextField()
    criteria = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user","badge")


# ---------- Marketplace & Wallets ----------

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="USD")


class Listing(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT)
    seller = models.ForeignKey(User, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="USD")
    status = models.CharField(max_length=8, choices=LISTING_STATUSES, default='ACTIVE')


class Purchase(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT)
    buyer = models.ForeignKey(User, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="USD")
    purchased_at = models.DateTimeField(default=timezone.now)


class Payout(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="USD")
    provider_ref = models.TextField()
    requested_at = models.DateTimeField(default=timezone.now)
    settled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=8, choices=PAYOUT_STATUSES, default='PENDING')

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(amount__gt=0), name="payout_amount_gt_0"),
        ]


# To-Do List for Classes

## Orgs
# - [X] Organization  
#   -> has many OrgMembership  
#   -> has many Course  

# - [X] OrgMembership  
#   -> belongs to Organization  
#   -> belongs to User  

## Courses & Enrollment
# - [X] Course  
#   -> belongs to Organization  
#   -> belongs to User (teacher)  
#   -> has many CourseMember  
#   -> has many Assignment  
#   -> has many LiveSession  

# - [X] CourseMember  
#   -> belongs to Course  
#   -> belongs to User  

## Quizzes & Content
# - [X] Quiz  
#   -> belongs to User (owner)  
#   -> has many QuizVersion  
#   -> has many QuizTag  
#   -> has many Assignment  
#   -> has many Listing  

# - [X] QuizVersion  
#   -> belongs to Quiz  
#   -> has many Question  
#   -> has many LiveSession  

# - [X] Question  
#   -> belongs to QuizVersion  
#   -> has many Choice  
#   -> has many QuestionMedia  
#   -> has many AttemptItem  

# - [X] Choice  
#   -> belongs to Question  
#   -> has many ChoiceMedia  

# - [X] QuestionMedia  
#   -> belongs to Question  

# - [X] ChoiceMedia  
#   -> belongs to Choice  

# - [X] Tag  
#   -> has many QuizTag  

# - [X] QuizTag  
#   -> belongs to Quiz  
#   -> belongs to Tag  

## Assignments & Attempts
# - [X] Assignment  
#   -> belongs to Course  
#   -> belongs to Quiz  
#   -> has many Attempt  

# - [X] Attempt  
#   -> belongs to Assignment  
#   -> belongs to User  
#   -> has one AttemptScore  
#   -> has many AttemptItem  

# - [X] AttemptItem  
#   -> belongs to Attempt  
#   -> belongs to Question  

# - [X] AttemptScore  
#   -> belongs to Attempt (OneToOne)  

## Live Sessions
# - [X] LiveSession  
#   -> belongs to QuizVersion  
#   -> belongs to Course  
#   -> belongs to User (host)  
#   -> has many LiveParticipant  
#   -> has many LiveEvent  
#   -> has many LiveLeaderboard  

# - [X] LiveParticipant  
#   -> belongs to LiveSession  
#   -> belongs to User  
#   -> has many LiveLeaderboard  

# - [X] LiveEvent  
#   -> belongs to LiveSession  

# - [X] LiveLeaderboard  
#   -> belongs to LiveSession  
#   -> belongs to LiveParticipant  

## Gamification
# - [X] XPTransaction  
#   -> belongs to User  

# - [X] Badge  
#   -> has many UserBadge  

# - [X] UserBadge  
#   -> belongs to User  
#   -> belongs to Badge  

## Marketplace & Wallets
# - [X] Wallet  
#   -> belongs to User (OneToOne)  
#   -> has many Payout  

# - [X] Listing  
#   -> belongs to Quiz  
#   -> belongs to User (seller)  
#   -> has many Purchase  

# - [X] Purchase  
#   -> belongs to Listing  
#   -> belongs to User (buyer)  

# - [X] Payout  
#   -> belongs to Wallet  


# Dependency Tree Map

# User
# ├── OrgMembership
# │   └── Organization
# │
# ├── Course
# │   ├── CourseMember
# │   ├── Assignment
# │   │   └── Attempt
# │   │       ├── AttemptScore
# │   │       └── AttemptItem
# │   │           └── Question
# │   │               └── QuizVersion
# │   │                   └── Quiz
# │   └── LiveSession
# │       ├── LiveParticipant
# │       │   └── LiveLeaderboard
# │       ├── LiveEvent
# │       └── LiveLeaderboard
# │
# ├── Quiz
# │   ├── QuizVersion
# │   │   └── Question
# │   │       ├── Choice
# │   │       │   └── ChoiceMedia
# │   │       ├── QuestionMedia
# │   │       └── AttemptItem (via Attempt)
# │   ├── QuizTag
# │   │   └── Tag
# │   └── Listing
# │       ├── Purchase
# │       └── Payout (via Wallet)
# │
# ├── Wallet
# │   └── Payout
# │
# ├── XPTransaction
# ├── Badge
# │   └── UserBadge
# │
# └── Organization
#     ├── OrgMembership
#     └── Course
