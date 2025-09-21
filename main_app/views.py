from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView

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
from .forms import (
    SignUpForm,
    OrganizationForm, OrgMembershipForm,
    CourseForm, CourseMemberForm,
    QuizForm, QuizVersionForm, QuestionForm, ChoiceForm, QuestionMediaForm, ChoiceMediaForm,
    TagForm, QuizTagForm,
    AssignmentForm, AttemptForm, AttemptItemForm, AttemptScoreForm,
    LiveSessionForm, LiveParticipantForm, LiveEventForm, LiveLeaderboardForm,
    XPTransactionForm, BadgeForm, UserBadgeForm,
    WalletForm, ListingForm, PurchaseForm, PayoutForm,
)

# Home
def home(request):
    if request.user.is_authenticated:
        return redirect("/organizations/")
    return render(request, "home.html")

# Auth
class SignUpView(FormView):
    template_name = "registration/signup.html"
    form_class = SignUpForm
    success_url = "/organizations/"

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)

class SignInView(LoginView):
    template_name = "registration/login.html"

class SignOutView(LogoutView):
    next_page = "/login/"

# Orgs
class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    paginate_by = 25
    ordering = ["name"]

class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    success_url = "/organizations/"

class OrganizationUpdateView(LoginRequiredMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    success_url = "/organizations/"

class OrganizationDeleteView(LoginRequiredMixin, DeleteView):
    model = Organization
    success_url = "/organizations/"

class OrgMembershipListView(LoginRequiredMixin, ListView):
    model = OrgMembership
    paginate_by = 25
    ordering = ["org_id","user_id"]

class OrgMembershipCreateView(LoginRequiredMixin, CreateView):
    model = OrgMembership
    form_class = OrgMembershipForm
    success_url = "/org-memberships/"

class OrgMembershipUpdateView(LoginRequiredMixin, UpdateView):
    model = OrgMembership
    form_class = OrgMembershipForm
    success_url = "/org-memberships/"

class OrgMembershipDeleteView(LoginRequiredMixin, DeleteView):
    model = OrgMembership
    success_url = "/org-memberships/"

# Courses
class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    paginate_by = 25
    ordering = ["name"]
    def get_queryset(self):
        return super().get_queryset().select_related("org","teacher")

class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    success_url = "/courses/"

class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    success_url = "/courses/"

class CourseDeleteView(LoginRequiredMixin, DeleteView):
    model = Course
    success_url = "/courses/"

class CourseMemberListView(LoginRequiredMixin, ListView):
    model = CourseMember
    paginate_by = 25
    ordering = ["course_id","user_id"]
    def get_queryset(self):
        return super().get_queryset().select_related("course","user")

class CourseMemberCreateView(LoginRequiredMixin, CreateView):
    model = CourseMember
    form_class = CourseMemberForm
    success_url = "/course-members/"

class CourseMemberUpdateView(LoginRequiredMixin, UpdateView):
    model = CourseMember
    form_class = CourseMemberForm
    success_url = "/course-members/"

class CourseMemberDeleteView(LoginRequiredMixin, DeleteView):
    model = CourseMember
    success_url = "/course-members/"

# Quizzes
class QuizListView(LoginRequiredMixin, ListView):
    model = Quiz
    paginate_by = 25
    ordering = ["title"]
    def get_queryset(self):
        return super().get_queryset().select_related("owner")

class QuizCreateView(LoginRequiredMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    success_url = "/quizzes/"

class QuizUpdateView(LoginRequiredMixin, UpdateView):
    model = Quiz
    form_class = QuizForm
    success_url = "/quizzes/"

class QuizDeleteView(LoginRequiredMixin, DeleteView):
    model = Quiz
    success_url = "/quizzes/"

class QuizVersionListView(LoginRequiredMixin, ListView):
    model = QuizVersion
    paginate_by = 25
    ordering = ["quiz_id","version_no"]
    def get_queryset(self):
        return super().get_queryset().select_related("quiz")

class QuizVersionCreateView(LoginRequiredMixin, CreateView):
    model = QuizVersion
    form_class = QuizVersionForm
    success_url = "/quiz-versions/"

class QuizVersionUpdateView(LoginRequiredMixin, UpdateView):
    model = QuizVersion
    form_class = QuizVersionForm
    success_url = "/quiz-versions/"

class QuizVersionDeleteView(LoginRequiredMixin, DeleteView):
    model = QuizVersion
    success_url = "/quiz-versions/"

class QuestionListView(LoginRequiredMixin, ListView):
    model = Question
    paginate_by = 25
    ordering = ["quiz_version_id","order_index"]
    def get_queryset(self):
        return super().get_queryset().select_related("quiz_version")

class QuestionCreateView(LoginRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    success_url = "/questions/"

class QuestionUpdateView(LoginRequiredMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    success_url = "/questions/"

class QuestionDeleteView(LoginRequiredMixin, DeleteView):
    model = Question
    success_url = "/questions/"

class ChoiceListView(LoginRequiredMixin, ListView):
    model = Choice
    paginate_by = 25
    ordering = ["question_id","order_index"]
    def get_queryset(self):
        return super().get_queryset().select_related("question")

class ChoiceCreateView(LoginRequiredMixin, CreateView):
    model = Choice
    form_class = ChoiceForm
    success_url = "/choices/"

class ChoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Choice
    form_class = ChoiceForm
    success_url = "/choices/"

class ChoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Choice
    success_url = "/choices/"

class QuestionMediaListView(LoginRequiredMixin, ListView):
    model = QuestionMedia
    paginate_by = 25
    ordering = ["question_id"]
    def get_queryset(self):
        return super().get_queryset().select_related("question")

class QuestionMediaCreateView(LoginRequiredMixin, CreateView):
    model = QuestionMedia
    form_class = QuestionMediaForm
    success_url = "/question-media/"

class QuestionMediaUpdateView(LoginRequiredMixin, UpdateView):
    model = QuestionMedia
    form_class = QuestionMediaForm
    success_url = "/question-media/"

class QuestionMediaDeleteView(LoginRequiredMixin, DeleteView):
    model = QuestionMedia
    success_url = "/question-media/"

class ChoiceMediaListView(LoginRequiredMixin, ListView):
    model = ChoiceMedia
    paginate_by = 25
    ordering = ["choice_id"]
    def get_queryset(self):
        return super().get_queryset().select_related("choice")

class ChoiceMediaCreateView(LoginRequiredMixin, CreateView):
    model = ChoiceMedia
    form_class = ChoiceMediaForm
    success_url = "/choice-media/"

class ChoiceMediaUpdateView(LoginRequiredMixin, UpdateView):
    model = ChoiceMedia
    form_class = ChoiceMediaForm
    success_url = "/choice-media/"

class ChoiceMediaDeleteView(LoginRequiredMixin, DeleteView):
    model = ChoiceMedia
    success_url = "/choice-media/"

class TagListView(LoginRequiredMixin, ListView):
    model = Tag
    paginate_by = 25
    ordering = ["name"]

class TagCreateView(LoginRequiredMixin, CreateView):
    model = Tag
    form_class = TagForm
    success_url = "/tags/"

class TagUpdateView(LoginRequiredMixin, UpdateView):
    model = Tag
    form_class = TagForm
    success_url = "/tags/"

class TagDeleteView(LoginRequiredMixin, DeleteView):
    model = Tag
    success_url = "/tags/"

class QuizTagListView(LoginRequiredMixin, ListView):
    model = QuizTag
    paginate_by = 25
    ordering = ["quiz_id","tag_id"]
    def get_queryset(self):
        return super().get_queryset().select_related("quiz","tag")

class QuizTagCreateView(LoginRequiredMixin, CreateView):
    model = QuizTag
    form_class = QuizTagForm
    success_url = "/quiz-tags/"

class QuizTagUpdateView(LoginRequiredMixin, UpdateView):
    model = QuizTag
    form_class = QuizTagForm
    success_url = "/quiz-tags/"

class QuizTagDeleteView(LoginRequiredMixin, DeleteView):
    model = QuizTag
    success_url = "/quiz-tags/"

# Assignments & Attempts
class AssignmentListView(LoginRequiredMixin, ListView):
    model = Assignment
    paginate_by = 25
    ordering = ["-open_at"]
    def get_queryset(self):
        return super().get_queryset().select_related("course","quiz")

class AssignmentCreateView(LoginRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    success_url = "/assignments/"

class AssignmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Assignment
    form_class = AssignmentForm
    success_url = "/assignments/"

class AssignmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Assignment
    success_url = "/assignments/"

class AttemptListView(LoginRequiredMixin, ListView):
    model = Attempt
    paginate_by = 25
    ordering = ["-started_at"]
    def get_queryset(self):
        return super().get_queryset().select_related("assignment","user")

class AttemptCreateView(LoginRequiredMixin, CreateView):
    model = Attempt
    form_class = AttemptForm
    success_url = "/attempts/"

class AttemptUpdateView(LoginRequiredMixin, UpdateView):
    model = Attempt
    form_class = AttemptForm
    success_url = "/attempts/"

class AttemptDeleteView(LoginRequiredMixin, DeleteView):
    model = Attempt
    success_url = "/attempts/"

class AttemptItemListView(LoginRequiredMixin, ListView):
    model = AttemptItem
    paginate_by = 25
    ordering = ["attempt_id","order_index"]
    def get_queryset(self):
        return super().get_queryset().select_related("attempt","question")

class AttemptItemCreateView(LoginRequiredMixin, CreateView):
    model = AttemptItem
    form_class = AttemptItemForm
    success_url = "/attempt-items/"

class AttemptItemUpdateView(LoginRequiredMixin, UpdateView):
    model = AttemptItem
    form_class = AttemptItemForm
    success_url = "/attempt-items/"

class AttemptItemDeleteView(LoginRequiredMixin, DeleteView):
    model = AttemptItem
    success_url = "/attempt-items/"

class AttemptScoreListView(LoginRequiredMixin, ListView):
    model = AttemptScore
    paginate_by = 25
    ordering = ["attempt_id"]
    def get_queryset(self):
        return super().get_queryset().select_related("attempt")

class AttemptScoreCreateView(LoginRequiredMixin, CreateView):
    model = AttemptScore
    form_class = AttemptScoreForm
    success_url = "/attempt-scores/"

class AttemptScoreUpdateView(LoginRequiredMixin, UpdateView):
    model = AttemptScore
    form_class = AttemptScoreForm
    success_url = "/attempt-scores/"

class AttemptScoreDeleteView(LoginRequiredMixin, DeleteView):
    model = AttemptScore
    success_url = "/attempt-scores/"

# Live Sessions
class LiveSessionListView(LoginRequiredMixin, ListView):
    model = LiveSession
    paginate_by = 25
    ordering = ["-started_at"]
    def get_queryset(self):
        return super().get_queryset().select_related("quiz_version","course","host")

class LiveSessionCreateView(LoginRequiredMixin, CreateView):
    model = LiveSession
    form_class = LiveSessionForm
    success_url = "/live-sessions/"

class LiveSessionUpdateView(LoginRequiredMixin, UpdateView):
    model = LiveSession
    form_class = LiveSessionForm
    success_url = "/live-sessions/"

class LiveSessionDeleteView(LoginRequiredMixin, DeleteView):
    model = LiveSession
    success_url = "/live-sessions/"

class LiveParticipantListView(LoginRequiredMixin, ListView):
    model = LiveParticipant
    paginate_by = 25
    ordering = ["session_id","nickname"]
    def get_queryset(self):
        return super().get_queryset().select_related("session","user")

class LiveParticipantCreateView(LoginRequiredMixin, CreateView):
    model = LiveParticipant
    form_class = LiveParticipantForm
    success_url = "/live-participants/"

class LiveParticipantUpdateView(LoginRequiredMixin, UpdateView):
    model = LiveParticipant
    form_class = LiveParticipantForm
    success_url = "/live-participants/"

class LiveParticipantDeleteView(LoginRequiredMixin, DeleteView):
    model = LiveParticipant
    success_url = "/live-participants/"

class LiveEventListView(LoginRequiredMixin, ListView):
    model = LiveEvent
    paginate_by = 25
    ordering = ["-ts"]
    def get_queryset(self):
        return super().get_queryset().select_related("session")

class LiveEventCreateView(LoginRequiredMixin, CreateView):
    model = LiveEvent
    form_class = LiveEventForm
    success_url = "/live-events/"

class LiveEventUpdateView(LoginRequiredMixin, UpdateView):
    model = LiveEvent
    form_class = LiveEventForm
    success_url = "/live-events/"

class LiveEventDeleteView(LoginRequiredMixin, DeleteView):
    model = LiveEvent
    success_url = "/live-events/"

class LiveLeaderboardListView(LoginRequiredMixin, ListView):
    model = LiveLeaderboard
    paginate_by = 25
    ordering = ["session_id","rank"]
    def get_queryset(self):
        return super().get_queryset().select_related("session","participant")

class LiveLeaderboardCreateView(LoginRequiredMixin, CreateView):
    model = LiveLeaderboard
    form_class = LiveLeaderboardForm
    success_url = "/live-leaderboard/"

class LiveLeaderboardUpdateView(LoginRequiredMixin, UpdateView):
    model = LiveLeaderboard
    form_class = LiveLeaderboardForm
    success_url = "/live-leaderboard/"

class LiveLeaderboardDeleteView(LoginRequiredMixin, DeleteView):
    model = LiveLeaderboard
    success_url = "/live-leaderboard/"

# Gamification
class XPTransactionListView(LoginRequiredMixin, ListView):
    model = XPTransaction
    paginate_by = 25
    ordering = ["-id"]
    def get_queryset(self):
        return super().get_queryset().select_related("user")

class XPTransactionCreateView(LoginRequiredMixin, CreateView):
    model = XPTransaction
    form_class = XPTransactionForm
    success_url = "/xp-transactions/"

class XPTransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = XPTransaction
    form_class = XPTransactionForm
    success_url = "/xp-transactions/"

class XPTransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = XPTransaction
    success_url = "/xp-transactions/"

class BadgeListView(LoginRequiredMixin, ListView):
    model = Badge
    paginate_by = 25
    ordering = ["code"]

class BadgeCreateView(LoginRequiredMixin, CreateView):
    model = Badge
    form_class = BadgeForm
    success_url = "/badges/"

class BadgeUpdateView(LoginRequiredMixin, UpdateView):
    model = Badge
    form_class = BadgeForm
    success_url = "/badges/"

class BadgeDeleteView(LoginRequiredMixin, DeleteView):
    model = Badge
    success_url = "/badges/"

class UserBadgeListView(LoginRequiredMixin, ListView):
    model = UserBadge
    paginate_by = 25
    ordering = ["user_id","badge_id"]
    def get_queryset(self):
        return super().get_queryset().select_related("user","badge")

class UserBadgeCreateView(LoginRequiredMixin, CreateView):
    model = UserBadge
    form_class = UserBadgeForm
    success_url = "/user-badges/"

class UserBadgeUpdateView(LoginRequiredMixin, UpdateView):
    model = UserBadge
    form_class = UserBadgeForm
    success_url = "/user-badges/"

class UserBadgeDeleteView(LoginRequiredMixin, DeleteView):
    model = UserBadge
    success_url = "/user-badges/"

# Marketplace & Wallets
class WalletListView(LoginRequiredMixin, ListView):
    model = Wallet
    paginate_by = 25
    ordering = ["user_id"]
    def get_queryset(self):
        return super().get_queryset().select_related("user")

class WalletCreateView(LoginRequiredMixin, CreateView):
    model = Wallet
    form_class = WalletForm
    success_url = "/wallets/"

class WalletUpdateView(LoginRequiredMixin, UpdateView):
    model = Wallet
    form_class = WalletForm
    success_url = "/wallets/"

class WalletDeleteView(LoginRequiredMixin, DeleteView):
    model = Wallet
    success_url = "/wallets/"

class ListingListView(LoginRequiredMixin, ListView):
    model = Listing
    paginate_by = 25
    ordering = ["-id"]
    def get_queryset(self):
        return super().get_queryset().select_related("quiz","seller")

class ListingCreateView(LoginRequiredMixin, CreateView):
    model = Listing
    form_class = ListingForm
    success_url = "/listings/"

class ListingUpdateView(LoginRequiredMixin, UpdateView):
    model = Listing
    form_class = ListingForm
    success_url = "/listings/"

class ListingDeleteView(LoginRequiredMixin, DeleteView):
    model = Listing
    success_url = "/listings/"

class PurchaseListView(LoginRequiredMixin, ListView):
    model = Purchase
    paginate_by = 25
    ordering = ["-purchased_at"]
    def get_queryset(self):
        return super().get_queryset().select_related("listing","buyer")

class PurchaseCreateView(LoginRequiredMixin, CreateView):
    model = Purchase
    form_class = PurchaseForm
    success_url = "/purchases/"

class PurchaseUpdateView(LoginRequiredMixin, UpdateView):
    model = Purchase
    form_class = PurchaseForm
    success_url = "/purchases/"

class PurchaseDeleteView(LoginRequiredMixin, DeleteView):
    model = Purchase
    success_url = "/purchases/"

class PayoutListView(LoginRequiredMixin, ListView):
    model = Payout
    paginate_by = 25
    ordering = ["-requested_at"]
    def get_queryset(self):
        return super().get_queryset().select_related("wallet")

class PayoutCreateView(LoginRequiredMixin, CreateView):
    model = Payout
    form_class = PayoutForm
    success_url = "/payouts/"

class PayoutUpdateView(LoginRequiredMixin, UpdateView):
    model = Payout
    form_class = PayoutForm
    success_url = "/payouts/"

class PayoutDeleteView(LoginRequiredMixin, DeleteView):
    model = Payout
    success_url = "/payouts/"
