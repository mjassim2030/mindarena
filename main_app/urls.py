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

]
