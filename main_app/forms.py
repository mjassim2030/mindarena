from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import (
    Organization, OrgMembership,
    Course, CourseMember,
    Quiz, QuizVersion, Question, Choice, QuestionMedia, ChoiceMedia,
    Tag, QuizTag,
    Assignment, Attempt, AttemptItem, AttemptScore,
    LiveSession, LiveParticipant, LiveEvent, LiveLeaderboard,
    XPTransaction, Badge, UserBadge,
    Wallet, Listing, Purchase, Payout,
)

# Auth
class SignUpForm(UserCreationForm):
    # Optional email field (keep or remove as you wish)
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ("username","email","password1","password2")


# Orgs
class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = "__all__"

class OrgMembershipForm(forms.ModelForm):
    class Meta:
        model = OrgMembership
        fields = "__all__"


# Courses
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = "__all__"

class CourseMemberForm(forms.ModelForm):
    class Meta:
        model = CourseMember
        fields = "__all__"


# Quizzes
class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = "__all__"

class QuizVersionForm(forms.ModelForm):
    class Meta:
        model = QuizVersion
        fields = "__all__"

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"
        widgets = {"meta": forms.Textarea(attrs={"rows": 3})}

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = "__all__"

class QuestionMediaForm(forms.ModelForm):
    class Meta:
        model = QuestionMedia
        fields = "__all__"
        widgets = {"attrib": forms.Textarea(attrs={"rows": 3})}

class ChoiceMediaForm(forms.ModelForm):
    class Meta:
        model = ChoiceMedia
        fields = "__all__"

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = "__all__"

class QuizTagForm(forms.ModelForm):
    class Meta:
        model = QuizTag
        fields = "__all__"


# Assignments & Attempts
class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = "__all__"
        widgets = {"settings": forms.Textarea(attrs={"rows": 3})}

class AttemptForm(forms.ModelForm):
    class Meta:
        model = Attempt
        fields = "__all__"

class AttemptItemForm(forms.ModelForm):
    class Meta:
        model = AttemptItem
        fields = "__all__"

class AttemptScoreForm(forms.ModelForm):
    class Meta:
        model = AttemptScore
        fields = "__all__"


# Live Sessions
class LiveSessionForm(forms.ModelForm):
    class Meta:
        model = LiveSession
        fields = "__all__"
        widgets = {"settings": forms.Textarea(attrs={"rows": 3})}

class LiveParticipantForm(forms.ModelForm):
    class Meta:
        model = LiveParticipant
        fields = "__all__"

class LiveEventForm(forms.ModelForm):
    class Meta:
        model = LiveEvent
        fields = "__all__"

class LiveLeaderboardForm(forms.ModelForm):
    class Meta:
        model = LiveLeaderboard
        fields = "__all__"


# Gamification
class XPTransactionForm(forms.ModelForm):
    class Meta:
        model = XPTransaction
        fields = "__all__"

class BadgeForm(forms.ModelForm):
    class Meta:
        model = Badge
        fields = "__all__"

class UserBadgeForm(forms.ModelForm):
    class Meta:
        model = UserBadge
        fields = "__all__"


# Marketplace & Wallets
class WalletForm(forms.ModelForm):
    class Meta:
        model = Wallet
        fields = "__all__"

class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = "__all__"

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = "__all__"

class PayoutForm(forms.ModelForm):
    class Meta:
        model = Payout
        fields = "__all__"
