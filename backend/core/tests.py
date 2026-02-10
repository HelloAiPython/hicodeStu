from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import ClassroomScore, Course, Enrollment, HomeworkScore, ScoreRule, StudentProfile


class LeaderboardApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username="teacher", password="pass123456", is_staff=True
        )
        self.client.force_authenticate(user=self.teacher)

        self.course = Course.objects.create(code="C001", name="数学", teacher=self.teacher)
        ScoreRule.objects.create(course=self.course, name="classroom", weight=Decimal("50.00"))
        ScoreRule.objects.create(course=self.course, name="homework", weight=Decimal("50.00"))

        self.students = []
        for index in range(1, 4):
            user = User.objects.create_user(username=f"stu{index}", password="pass123456")
            profile = StudentProfile.objects.create(
                user=user,
                student_number=f"S00{index}",
                enrollment_year=2024,
                major="CS",
            )
            enrollment = Enrollment.objects.create(student=profile, course=self.course)
            self.students.append((profile, enrollment))

        # S001 total -> 92
        ClassroomScore.objects.create(
            enrollment=self.students[0][1],
            attentive=95,
            participation=90,
            exercise_completion=91,
        )
        HomeworkScore.objects.create(
            enrollment=self.students[0][1], completion=93, accuracy=92, correction=91
        )

        # S002 total -> 75
        ClassroomScore.objects.create(
            enrollment=self.students[1][1], attentive=75, participation=74, exercise_completion=76
        )
        HomeworkScore.objects.create(
            enrollment=self.students[1][1], completion=74, accuracy=76, correction=75
        )

        # S003 pending (no scores)

    def test_leaderboard_default(self):
        response = self.client.get(f"/api/courses/{self.course.id}/leaderboard/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["results"][0]["student_number"], "S001")

    def test_leaderboard_only_scored_and_min_score(self):
        response = self.client.get(
            f"/api/courses/{self.course.id}/leaderboard/?only_scored=1&min_score=80"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["student_number"], "S001")

    def test_leaderboard_student_number_and_limit(self):
        response = self.client.get(
            f"/api/courses/{self.course.id}/leaderboard/?student_number=S00&limit=1"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)
