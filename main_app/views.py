from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView

from .models import (
    Organization
)
from .forms import (
    SignUpForm,
    OrganizationForm
)

# ---------- Home ----------
def home(request):
    if request.user.is_authenticated:
        return redirect("/organizations/")
    return render(request, "home.html")

# ---------- Auth ----------
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
