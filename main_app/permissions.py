# apps/orgs/permissions.py
from .models import OrgMembership

# Models
ORG = "organization"
MEMBERSHIP = "orgmembership"
COURSE = "course"
QUIZ = "quiz"
LIVE_SESSION = "livesession"
LIVE_PARTICIPANT = "liveparticipant"
LIVE_LEADERBOARD = "liveleaderboard"

# Actions
CREATE = "create"
READ_ALL = "read_all"
READ_ONE = "read_one"
UPDATE_ONE = "update_one"
DELETE_ALL = "delete_all"
DELETE_ONE = "delete_one"

ROLE_ACTIONS = {
    "superuser": {
        ORG: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        MEMBERSHIP:{CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        COURSE: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        QUIZ: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_SESSION: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_PARTICIPANT:{CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_LEADERBOARD:{CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},

    },
    "admin": {
        ORG: {CREATE, READ_ONE, UPDATE_ONE, DELETE_ONE},
        MEMBERSHIP: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        COURSE: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ONE, DELETE_ALL},
        QUIZ: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_SESSION: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_PARTICIPANT:{CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_LEADERBOARD:{CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},

    },
    "manager": {
        ORG: {READ_ONE, UPDATE_ONE},
        MEMBERSHIP: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE},
        COURSE: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE},
        QUIZ: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_SESSION: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_PARTICIPANT:{READ_ALL, READ_ONE},
        LIVE_LEADERBOARD:{READ_ALL, READ_ONE},

    },
    "teacher": {
        ORG: {READ_ONE},
        MEMBERSHIP: {READ_ALL, READ_ONE},
        COURSE: {READ_ALL, READ_ONE},
        QUIZ: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_SESSION: {CREATE, READ_ALL, READ_ONE, UPDATE_ONE, DELETE_ALL, DELETE_ONE},
        LIVE_PARTICIPANT:{READ_ALL, READ_ONE},
        LIVE_LEADERBOARD:{READ_ALL, READ_ONE}, 

    },
    "student": {
        ORG: {READ_ONE},
        MEMBERSHIP: set(),
        COURSE: {READ_ALL, READ_ONE},
        QUIZ: {READ_ALL, READ_ONE},
        LIVE_SESSION:{READ_ALL, READ_ONE},
        LIVE_PARTICIPANT:{READ_ALL},
        LIVE_LEADERBOARD:{READ_ALL},
    },
    "parents": {
        ORG: {READ_ONE},
        MEMBERSHIP: set(),
        COURSE: {READ_ALL, READ_ONE},
        QUIZ: {READ_ALL, READ_ONE},
        LIVE_SESSION: {READ_ALL, READ_ONE},
        LIVE_PARTICIPANT:{READ_ALL},
        LIVE_LEADERBOARD:{READ_ALL},

    },
}

def allowed(user, action: str, model: str, org=None) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if org is None:
        return False
    try:
        role = (
            OrgMembership.objects.only("role")
            .get(user=user, organization=org)
            .role.lower()
        )
    except OrgMembership.DoesNotExist:
        return False
    return action in ROLE_ACTIONS.get(role, {}).get(model, set())
