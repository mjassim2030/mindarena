from django import template
from main_app.models import OrgMembership
from main_app.permissions import (
    allowed,
    ORG,
    COURSE,
    QUIZ,
    LIVE_SESSION,
    LIVE_PARTICIPANT,
    READ_ALL,
)

register = template.Library()


def _actor_org(user):
    if not getattr(user, "is_authenticated", False):
        return None
    m = (
        OrgMembership.objects.select_related("organization")
        .only("organization")
        .filter(user=user)
        .first()
    )
    return m.organization if m else None


@register.filter
def can_read_all_orgs(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    org = _actor_org(user)
    return allowed(user, READ_ALL, ORG, org=org) if org else False


@register.filter
def can_view_courses(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    org = _actor_org(user)
    return allowed(user, READ_ALL, COURSE, org=org) if org else False


@register.filter
def can_view_quizzes(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    org = _actor_org(user)
    return allowed(user, READ_ALL, QUIZ, org=org) if org else False


@register.filter
def can_view_livesessions(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    org = _actor_org(user)
    return allowed(user, READ_ALL, LIVE_SESSION, org=org) if org else False


@register.filter
def can_view_liveparticipants(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    org = _actor_org(user)
    return allowed(user, READ_ALL, LIVE_PARTICIPANT, org=org) if org else False


@register.filter
def is_student_or_parent(user):
    if not getattr(user, "is_authenticated", False):
        return False
    # Show quick "Join Live" only if user has at least one membership as student/parents
    return OrgMembership.objects.filter(user=user, role__in=["student", "parents"]).exists()
