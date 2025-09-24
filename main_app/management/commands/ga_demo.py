from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import get_random_string

from main_app.models import Organization, OrgMembership, Course, Quiz, _short_code
from main_app.constants import ROLE_ADMIN, ROLE_TEACHER, ROLE_SUPERUSER

User = get_user_model()

def _subject_default():
    """Pick a safe subject_category value even if choices/defaults differ per project."""
    field = Course._meta.get_field("subject_category")
    # Prefer explicit default if present
    try:
        if getattr(field, "has_default", None) and field.has_default():
            return field.default() if callable(field.default) else field.default
    except Exception:
        pass
    # Otherwise, first choice if defined, else 0
    try:
        choices = getattr(field, "choices", None)
        if choices:
            return choices[0][0]
    except Exception:
        pass
    return 0

def _q(question, qtype="MCQ", image=None, choices=None):
    """Build a question dict compatible with your app."""
    return {
        "question": question,
        "question_type": qtype,  # "MCQ" | "MSQ" | "TF"
        "image": image,
        "choices": choices or [],
    }

class Command(BaseCommand):
    help = "Seeds a demo org, superuser, teacher, course, and quizzes with mixed question types."

    @transaction.atomic
    def handle(self, *args, **opts):
        # 0) Superuser spk
        su, created_su = User.objects.get_or_create(
            username="spk",
            defaults={"email": "spk@example.com", "is_superuser": True, "is_staff": True},
        )
        su.is_superuser = True
        su.is_staff = True
        su.set_password("mind@123")
        su.save()

        # 1) admin
        ad, created_ad = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@example.com", "is_superuser": False, "is_staff": True},
        )
        ad.is_superuser = False
        ad.is_staff = True
        ad.set_password("mind@123") 
        ad.save()

        # 2) Organization
        org, _ = Organization.objects.get_or_create(name="General Assembly (Demo)")

        # Ensure the superuser is a member (admin) of this org too
        OrgMembership.objects.get_or_create(organization=org, user=su, defaults={"role": ROLE_SUPERUSER})
        OrgMembership.objects.get_or_create(organization=org, user=ad, defaults={"role": ROLE_ADMIN})

        # 3) Teacher user
        teacher, created_teacher = User.objects.get_or_create(
            username="ga_instructor",
            defaults={"email": "ga_instructor@example.com"},
        )
        if created_teacher:
            teacher.set_password("teach@123")  # dev/demo convenience
            teacher.first_name = "GA"
            teacher.last_name = "Instructor"
            teacher.save()

        OrgMembership.objects.get_or_create(
            organization=org, user=teacher, defaults={"role": ROLE_TEACHER}
        )

        # 4) Course
        course, _ = Course.objects.get_or_create(
            organization=org,
            teacher=teacher,
            course_name="Software Engineering Fundamentals",
            defaults={
                "join_code": _short_code()[:8],
                "subject_category": _subject_default(),
                "enrolled_students": [],
            },
        )

        # 5) Quizzes (+ mixed question types + images)
        #    (Images are Wikimedia Commons links—fine for demo usage.)
        img_lab = "https://upload.wikimedia.org/wikipedia/commons/5/5e/Argostoli_1st_Middle_School_student_computer_lab_4.jpg"
        img_prof = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/A_college_professor_teaching_in_a_university_classroom_full_of_students_in_Tennessee%2C_United_States_09.jpg/1024px-A_college_professor_teaching_in_a_university_classroom_full_of_students_in_Tennessee%2C_United_States_09.jpg"
        img_feedback = "https://upload.wikimedia.org/wikipedia/commons/5/58/Feedback.png"
        img_computer_lab = "https://upload.wikimedia.org/wikipedia/commons/1/1e/Computer_Lab_Picture.jpg"

        quizzes_spec = [
            {
                "title": "GA Orientation",
                "questions": [
                    _q(
                        "Which best describes your familiarity with General Assembly before enrolling?",
                        "MCQ",
                        img_lab,
                        [
                            {"text": "New to GA", "is_correct": True},
                            {"text": "Heard about it", "is_correct": False},
                            {"text": "Alumni referral", "is_correct": False},
                        ],
                    ),
                    _q(
                        "Select all the channels you used to learn about the program.",
                        "MSQ",
                        None,
                        [
                            {"text": "GA Website", "is_correct": True},
                            {"text": "Social Media", "is_correct": True},
                            {"text": "Random Guess", "is_correct": False},
                            {"text": "Friend/Alumni", "is_correct": True},
                        ],
                    ),
                    _q(
                        "Orientation explained expectations clearly.",
                        "TF",
                        None,
                        [
                            {"text": "True", "is_correct": True},
                            {"text": "False", "is_correct": False},
                        ],
                    ),
                ],
            },
            {
                "title": "SE Program Feedback",
                "questions": [
                    _q(
                        "How would you rate the overall pace of the Software Engineering course?",
                        "MCQ",
                        img_prof,
                        [
                            {"text": "Too slow", "is_correct": False},
                            {"text": "Just right", "is_correct": True},
                            {"text": "Too fast", "is_correct": False},
                        ],
                    ),
                    _q(
                        "Which parts were most helpful? (Select all that apply)",
                        "MSQ",
                        img_computer_lab,
                        [
                            {"text": "Pair programming", "is_correct": True},
                            {"text": "Projects", "is_correct": True},
                            {"text": "Daily standups", "is_correct": True},
                            {"text": "Skipping exercises", "is_correct": False},
                        ],
                    ),
                    _q(
                        "Unit projects improved my understanding of real-world workflows.",
                        "TF",
                        None,
                        [
                            {"text": "True", "is_correct": True},
                            {"text": "False", "is_correct": False},
                        ],
                    ),
                    _q(
                        "Which topics would you like more practice with?",
                        "MCQ",
                        None,
                        [
                            {"text": "APIs & Auth", "is_correct": True},
                            {"text": "Version Control", "is_correct": False},
                            {"text": "HTML/CSS", "is_correct": False},
                        ],
                    ),
                ],
            },
            {
                "title": "Instructor & IAs",
                "questions": [
                    _q(
                        "My instructor’s explanations were clear.",
                        "TF",
                        img_feedback,
                        [
                            {"text": "True", "is_correct": True},
                            {"text": "False", "is_correct": False},
                        ],
                    ),
                    _q(
                        "Which IA supports did you use? (Select all that apply)",
                        "MSQ",
                        None,
                        [
                            {"text": "Office hours", "is_correct": True},
                            {"text": "1:1 help", "is_correct": True},
                            {"text": "Class Slack Q&A", "is_correct": True},
                            {"text": "None of the above", "is_correct": False},
                        ],
                    ),
                    _q(
                        "How satisfied are you with feedback turnaround?",
                        "MCQ",
                        None,
                        [
                            {"text": "Unsatisfied", "is_correct": False},
                            {"text": "Satisfied", "is_correct": True},
                            {"text": "Very satisfied", "is_correct": False},
                        ],
                    ),
                ],
            },
        ]

        created_titles = []
        for spec in quizzes_spec:
            quiz, _ = Quiz.objects.get_or_create(
                course=course, quiz_title=spec["title"], defaults={"content": []}
            )
            # Always (re)write content to ensure shape is correct
            quiz.content = spec["questions"]
            quiz.save(update_fields=["content"])
            created_titles.append(quiz.quiz_title)

        self.stdout.write(self.style.SUCCESS("✅ Seed complete!"))
        self.stdout.write(f"  Org: {org.name}")
        self.stdout.write(f"  Superuser: spk / mind@123")
        self.stdout.write(f"  Teacher: ga_instructor / teach@123")
        self.stdout.write(f"  Course: {course.course_name}  (join_code: {course.join_code})")
        self.stdout.write("  Quizzes:")
        for t in created_titles:
            self.stdout.write(f"    - {t}")
