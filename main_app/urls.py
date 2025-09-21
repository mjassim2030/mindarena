from django.urls import path
from . import views

app_name = "main_app"

urlpatterns = [
    path("", views.home, name="home"),

    # Auth
    path("accounts/signup/", views.SignUpView.as_view(), name="signup"),
    path("accounts/login/",  views.SignInView.as_view(),  name="login"),
    path("accounts/logout/", views.SignOutView.as_view(), name="logout"),

    # Orgs
    path("organizations/", views.OrganizationListView.as_view(), name="organization_list"),
    path("organizations/create/", views.OrganizationCreateView.as_view(), name="organization_create"),
    path("organizations/<int:pk>/update/", views.OrganizationUpdateView.as_view(), name="organization_update"),
    path("organizations/<int:pk>/delete/", views.OrganizationDeleteView.as_view(), name="organization_delete"),

    path("org-memberships/", views.OrgMembershipListView.as_view(), name="orgmembership_list"),
    path("org-memberships/create/", views.OrgMembershipCreateView.as_view(), name="orgmembership_create"),
    path("org-memberships/<int:pk>/update/", views.OrgMembershipUpdateView.as_view(), name="orgmembership_update"),
    path("org-memberships/<int:pk>/delete/", views.OrgMembershipDeleteView.as_view(), name="orgmembership_delete"),

    # Courses & Enrollment
    path("courses/", views.CourseListView.as_view(), name="course_list"),
    path("courses/create/", views.CourseCreateView.as_view(), name="course_create"),
    path("courses/<int:pk>/update/", views.CourseUpdateView.as_view(), name="course_update"),
    path("courses/<int:pk>/delete/", views.CourseDeleteView.as_view(), name="course_delete"),

    path("course-members/", views.CourseMemberListView.as_view(), name="coursemember_list"),
    path("course-members/create/", views.CourseMemberCreateView.as_view(), name="coursemember_create"),
    path("course-members/<int:pk>/update/", views.CourseMemberUpdateView.as_view(), name="coursemember_update"),
    path("course-members/<int:pk>/delete/", views.CourseMemberDeleteView.as_view(), name="coursemember_delete"),

    # Quizzes
    path("quizzes/", views.QuizListView.as_view(), name="quiz_list"),
    path("quizzes/create/", views.QuizCreateView.as_view(), name="quiz_create"),
    path("quizzes/<int:pk>/update/", views.QuizUpdateView.as_view(), name="quiz_update"),
    path("quizzes/<int:pk>/delete/", views.QuizDeleteView.as_view(), name="quiz_delete"),

    path("quiz-versions/", views.QuizVersionListView.as_view(), name="quizversion_list"),
    path("quiz-versions/create/", views.QuizVersionCreateView.as_view(), name="quizversion_create"),
    path("quiz-versions/<int:pk>/update/", views.QuizVersionUpdateView.as_view(), name="quizversion_update"),
    path("quiz-versions/<int:pk>/delete/", views.QuizVersionDeleteView.as_view(), name="quizversion_delete"),

    path("questions/", views.QuestionListView.as_view(), name="question_list"),
    path("questions/create/", views.QuestionCreateView.as_view(), name="question_create"),
    path("questions/<int:pk>/update/", views.QuestionUpdateView.as_view(), name="question_update"),
    path("questions/<int:pk>/delete/", views.QuestionDeleteView.as_view(), name="question_delete"),

    path("choices/", views.ChoiceListView.as_view(), name="choice_list"),
    path("choices/create/", views.ChoiceCreateView.as_view(), name="choice_create"),
    path("choices/<int:pk>/update/", views.ChoiceUpdateView.as_view(), name="choice_update"),
    path("choices/<int:pk>/delete/", views.ChoiceDeleteView.as_view(), name="choice_delete"),

    path("question-media/", views.QuestionMediaListView.as_view(), name="questionmedia_list"),
    path("question-media/create/", views.QuestionMediaCreateView.as_view(), name="questionmedia_create"),
    path("question-media/<int:pk>/update/", views.QuestionMediaUpdateView.as_view(), name="questionmedia_update"),
    path("question-media/<int:pk>/delete/", views.QuestionMediaDeleteView.as_view(), name="questionmedia_delete"),

    path("choice-media/", views.ChoiceMediaListView.as_view(), name="choicemedia_list"),
    path("choice-media/create/", views.ChoiceMediaCreateView.as_view(), name="choicemedia_create"),
    path("choice-media/<int:pk>/update/", views.ChoiceMediaUpdateView.as_view(), name="choicemedia_update"),
    path("choice-media/<int:pk>/delete/", views.ChoiceMediaDeleteView.as_view(), name="choicemedia_delete"),

    path("tags/", views.TagListView.as_view(), name="tag_list"),
    path("tags/create/", views.TagCreateView.as_view(), name="tag_create"),
    path("tags/<int:pk>/update/", views.TagUpdateView.as_view(), name="tag_update"),
    path("tags/<int:pk>/delete/", views.TagDeleteView.as_view(), name="tag_delete"),

    path("quiz-tags/", views.QuizTagListView.as_view(), name="quiztag_list"),
    path("quiz-tags/create/", views.QuizTagCreateView.as_view(), name="quiztag_create"),
    path("quiz-tags/<int:pk>/update/", views.QuizTagUpdateView.as_view(), name="quiztag_update"),
    path("quiz-tags/<int:pk>/delete/", views.QuizTagDeleteView.as_view(), name="quiztag_delete"),

    # Assignments & Attempts
    path("assignments/", views.AssignmentListView.as_view(), name="assignment_list"),
    path("assignments/create/", views.AssignmentCreateView.as_view(), name="assignment_create"),
    path("assignments/<int:pk>/update/", views.AssignmentUpdateView.as_view(), name="assignment_update"),
    path("assignments/<int:pk>/delete/", views.AssignmentDeleteView.as_view(), name="assignment_delete"),

    path("attempts/", views.AttemptListView.as_view(), name="attempt_list"),
    path("attempts/create/", views.AttemptCreateView.as_view(), name="attempt_create"),
    path("attempts/<int:pk>/update/", views.AttemptUpdateView.as_view(), name="attempt_update"),
    path("attempts/<int:pk>/delete/", views.AttemptDeleteView.as_view(), name="attempt_delete"),

    path("attempt-items/", views.AttemptItemListView.as_view(), name="attemptitem_list"),
    path("attempt-items/create/", views.AttemptItemCreateView.as_view(), name="attemptitem_create"),
    path("attempt-items/<int:pk>/update/", views.AttemptItemUpdateView.as_view(), name="attemptitem_update"),
    path("attempt-items/<int:pk>/delete/", views.AttemptItemDeleteView.as_view(), name="attemptitem_delete"),

    path("attempt-scores/", views.AttemptScoreListView.as_view(), name="attemptscore_list"),
    path("attempt-scores/create/", views.AttemptScoreCreateView.as_view(), name="attemptscore_create"),
    path("attempt-scores/<int:pk>/update/", views.AttemptScoreUpdateView.as_view(), name="attemptscore_update"),
    path("attempt-scores/<int:pk>/delete/", views.AttemptScoreDeleteView.as_view(), name="attemptscore_delete"),

    # Live Sessions
    path("live-sessions/", views.LiveSessionListView.as_view(), name="livesession_list"),
    path("live-sessions/create/", views.LiveSessionCreateView.as_view(), name="livesession_create"),
    path("live-sessions/<int:pk>/update/", views.LiveSessionUpdateView.as_view(), name="livesession_update"),
    path("live-sessions/<int:pk>/delete/", views.LiveSessionDeleteView.as_view(), name="livesession_delete"),

    path("live-participants/", views.LiveParticipantListView.as_view(), name="liveparticipant_list"),
    path("live-participants/create/", views.LiveParticipantCreateView.as_view(), name="liveparticipant_create"),
    path("live-participants/<int:pk>/update/", views.LiveParticipantUpdateView.as_view(), name="liveparticipant_update"),
    path("live-participants/<int:pk>/delete/", views.LiveParticipantDeleteView.as_view(), name="liveparticipant_delete"),

    path("live-events/", views.LiveEventListView.as_view(), name="liveevent_list"),
    path("live-events/create/", views.LiveEventCreateView.as_view(), name="liveevent_create"),
    path("live-events/<int:pk>/update/", views.LiveEventUpdateView.as_view(), name="liveevent_update"),
    path("live-events/<int:pk>/delete/", views.LiveEventDeleteView.as_view(), name="liveevent_delete"),

    path("live-leaderboard/", views.LiveLeaderboardListView.as_view(), name="liveleaderboard_list"),
    path("live-leaderboard/create/", views.LiveLeaderboardCreateView.as_view(), name="liveleaderboard_create"),
    path("live-leaderboard/<int:pk>/update/", views.LiveLeaderboardUpdateView.as_view(), name="liveleaderboard_update"),
    path("live-leaderboard/<int:pk>/delete/", views.LiveLeaderboardDeleteView.as_view(), name="liveleaderboard_delete"),

    # Gamification
    path("xp-transactions/", views.XPTransactionListView.as_view(), name="xptransaction_list"),
    path("xp-transactions/create/", views.XPTransactionCreateView.as_view(), name="xptransaction_create"),
    path("xp-transactions/<int:pk>/update/", views.XPTransactionUpdateView.as_view(), name="xptransaction_update"),
    path("xp-transactions/<int:pk>/delete/", views.XPTransactionDeleteView.as_view(), name="xptransaction_delete"),

    path("badges/", views.BadgeListView.as_view(), name="badge_list"),
    path("badges/create/", views.BadgeCreateView.as_view(), name="badge_create"),
    path("badges/<int:pk>/update/", views.BadgeUpdateView.as_view(), name="badge_update"),
    path("badges/<int:pk>/delete/", views.BadgeDeleteView.as_view(), name="badge_delete"),

    path("user-badges/", views.UserBadgeListView.as_view(), name="userbadge_list"),
    path("user-badges/create/", views.UserBadgeCreateView.as_view(), name="userbadge_create"),
    path("user-badges/<int:pk>/update/", views.UserBadgeUpdateView.as_view(), name="userbadge_update"),
    path("user-badges/<int:pk>/delete/", views.UserBadgeDeleteView.as_view(), name="userbadge_delete"),

    # Marketplace & Wallets
    path("wallets/", views.WalletListView.as_view(), name="wallet_list"),
    path("wallets/create/", views.WalletCreateView.as_view(), name="wallet_create"),
    path("wallets/<int:pk>/update/", views.WalletUpdateView.as_view(), name="wallet_update"),
    path("wallets/<int:pk>/delete/", views.WalletDeleteView.as_view(), name="wallet_delete"),

    path("listings/", views.ListingListView.as_view(), name="listing_list"),
    path("listings/create/", views.ListingCreateView.as_view(), name="listing_create"),
    path("listings/<int:pk>/update/", views.ListingUpdateView.as_view(), name="listing_update"),
    path("listings/<int:pk>/delete/", views.ListingDeleteView.as_view(), name="listing_delete"),

    path("purchases/", views.PurchaseListView.as_view(), name="purchase_list"),
    path("purchases/create/", views.PurchaseCreateView.as_view(), name="purchase_create"),
    path("purchases/<int:pk>/update/", views.PurchaseUpdateView.as_view(), name="purchase_update"),
    path("purchases/<int:pk>/delete/", views.PurchaseDeleteView.as_view(), name="purchase_delete"),

    path("payouts/", views.PayoutListView.as_view(), name="payout_list"),
    path("payouts/create/", views.PayoutCreateView.as_view(), name="payout_create"),
    path("payouts/<int:pk>/update/", views.PayoutUpdateView.as_view(), name="payout_update"),
    path("payouts/<int:pk>/delete/", views.PayoutDeleteView.as_view(), name="payout_delete"),

]
