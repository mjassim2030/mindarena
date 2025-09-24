from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.home, name="home"),

    # Auth
    path("signup/", views.signup, name="signup"),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    path("join/", views.join_organization, name="join_organization"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Auth aliases
    path("accounts/login/", views.SignInView.as_view(), name="login_alias"),
    path("accounts/logout/", views.SignOutView.as_view(), name="logout_alias"),
    path("accounts/signup/", views.signup, name="signup_alias"),

    # Organizations / Members
    path("organizations/", views.OrganizationListView.as_view(), name="organization_list"),
    path("members/create/", views.orgmember_create, name="orgmember_create"),
    path("members/<int:pk>/edit/", views.orgmember_edit, name="orgmember_edit"),
    path("members/<int:pk>/delete/", views.orgmember_delete, name="orgmember_delete"),

    # Courses
    path("courses/", views.course_list, name="course_list"),
    path("courses/create/", views.course_create, name="course_create"),
    path("courses/join/", views.course_join, name="course_join"),   # ← added
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),

    # Quizzes
    path("quizzes/", views.quiz_list, name="quiz_list"),
    path("quizzes/create/", views.quiz_create, name="quiz_create"),
    path("quizzes/<int:pk>/", views.quiz_detail, name="quiz_detail"),
    path("quizzes/<int:pk>/edit/", views.quiz_edit, name="quiz_edit"),
    path("quizzes/<int:pk>/delete/", views.quiz_delete, name="quiz_delete"),

    # Quiz Questions
    path("quizzes/<int:pk>/questions/", views.quiz_questions, name="quiz_questions"),
    path("quizzes/<int:pk>/questions/add/", views.quiz_question_add, name="quiz_question_add"),
    path("quizzes/<int:pk>/questions/<int:qindex>/edit/", views.quiz_question_edit, name="quiz_question_edit"),
    path("quizzes/<int:pk>/questions/<int:qindex>/delete/", views.quiz_question_delete, name="quiz_question_delete"),
    path("quizzes/<int:pk>/questions/<int:qindex>/<str:direction>/", views.quiz_question_move, name="quiz_question_move"),

    # Live Sessions
    path("live/create/<int:quiz_id>/", views.livesession_create, name="livesession_create"),
    path("live/session/<int:pk>/", views.livesession_detail, name="livesession_detail"),
    path("live/session/<int:pk>/play/", views.livesession_play, name="livesession_play"),
    path("live/join/", views.livesession_join, name="livesession_join"),
    path("live/session/<int:pk>/status/", views.livesession_status, name="livesession_status"),
    path("live/session/<int:pk>/answers/", views.livesession_answers, name="livesession_answers"),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
