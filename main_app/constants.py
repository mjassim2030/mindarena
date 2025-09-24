ROLE_SUPERUSER = "superuser"
ROLE_ADMIN     = "admin"
ROLE_MANAGER   = "manager"
ROLE_TEACHER   = "teacher"
ROLE_STUDENT   = "student"
ROLE_PARENTS   = "parents"

ROLE_CHOICES = (
    (ROLE_SUPERUSER, "Superuser"),
    (ROLE_ADMIN,     "Admin"),
    (ROLE_MANAGER,   "Manager"),
    (ROLE_TEACHER,   "Teacher"),
    (ROLE_STUDENT,   "Student"),
    (ROLE_PARENTS,   "Parents"),
)

DEFAULT_ROLE = ROLE_STUDENT

SUBJECT_CATEGORIES = (
    ("math", "Math"),
    ("science", "Science"),
    ("language", "Language"),
    ("history", "History"),
    ("technology", "Technology"),
    ("arts", "Arts"),
)
