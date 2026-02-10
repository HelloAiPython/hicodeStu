from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import ClassroomScore, Course, Enrollment, HomeworkScore, ScoreRule, StudentProfile


class BaseApiFixture(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.teacher = user_model.objects.create_user(
            username="teacher", password="pass123456", is_staff=True
        )
        self.client.force_authenticate(user=self.teacher)

        self.course = Course.objects.create(code="C001", name="数学", teacher=self.teacher)
        ScoreRule.objects.create(course=self.course, name="classroom", weight=Decimal("50.00"))
        ScoreRule.objects.create(course=self.course, name="homework", weight=Decimal("50.00"))

        self.students = []
        for index in range(1, 4):
            user = user_model.objects.create_user(username=f"stu{index}", password="pass123456")
            profile = StudentProfile.objects.create(
                user=user,
                student_number=f"S00{index}",
                enrollment_year=2024,
                major="CS",
            )
            enrollment = Enrollment.objects.create(student=profile, course=self.course)
            self.students.append((profile, enrollment))

        ClassroomScore.objects.create(
            enrollment=self.students[0][1],
            attentive=95,
            participation=90,
            exercise_completion=91,
        )
        HomeworkScore.objects.create(
            enrollment=self.students[0][1], completion=93, accuracy=92, correction=91
        )

        ClassroomScore.objects.create(
            enrollment=self.students[1][1], attentive=75, participation=74, exercise_completion=76
        )
        HomeworkScore.objects.create(
            enrollment=self.students[1][1], completion=74, accuracy=76, correction=75
        )


class LeaderboardApiTests(BaseApiFixture):
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


    def test_leaderboard_pagination(self):
        response = self.client.get(
            f"/api/courses/{self.course.id}/leaderboard/?only_scored=1&page=1&page_size=1"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 1)
        self.assertEqual(len(data["results"]), 1)

    def test_leaderboard_student_number_and_limit(self):
        response = self.client.get(
            f"/api/courses/{self.course.id}/leaderboard/?student_number=S00&limit=1"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)



    def test_leaderboard_export_csv(self):
        response = self.client.get(f"/api/courses/{self.course.id}/leaderboard_export/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment; filename=", response["Content-Disposition"])

    def test_report_export_csv(self):
        response = self.client.get(f"/api/courses/{self.course.id}/report_export/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment; filename=", response["Content-Disposition"])

    def test_course_global_overview(self):
        response = self.client.get("/api/courses/global_overview/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course_count"], 1)
        self.assertEqual(data["student_count"], 3)
        self.assertEqual(data["enrollment_count"], 3)
        self.assertEqual(data["fully_scored_enrollment_count"], 2)
        self.assertEqual(data["pending_enrollment_count"], 1)


    def test_score_rule_validate_weights(self):
        response = self.client.get(f"/api/score-rules/validate/?course_id={self.course.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_weight"], 100.0)
        self.assertTrue(data["is_valid"])

    def test_score_rule_validate_weights_missing_course_id(self):
        response = self.client.get("/api/score-rules/validate/")
        self.assertEqual(response.status_code, 400)

    def test_score_rule_normalize_weights(self):
        ScoreRule.objects.filter(course=self.course, name="classroom").update(weight=Decimal("70.00"))
        ScoreRule.objects.filter(course=self.course, name="homework").update(weight=Decimal("50.00"))

        response = self.client.post(
            "/api/score-rules/normalize/",
            {"course_id": self.course.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_weight"], 100.0)
        self.assertTrue(data["is_valid"])

    def test_score_rule_normalize_weights_missing_course_id(self):
        response = self.client.post("/api/score-rules/normalize/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_score_rule_audit_weights(self):
        response = self.client.get("/api/score-rules/audit/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course_count"], 1)
        self.assertEqual(data["invalid_count"], 0)
        self.assertTrue(data["results"][0]["is_valid"])

    def test_score_rule_audit_weights_invalid_course(self):
        ScoreRule.objects.filter(course=self.course, name="classroom").update(weight=Decimal("60.00"))
        ScoreRule.objects.filter(course=self.course, name="homework").update(weight=Decimal("30.00"))
        response = self.client.get("/api/score-rules/audit/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["invalid_count"], 1)
        self.assertFalse(data["results"][0]["is_valid"])

    def test_enrollment_bulk_create(self):
        extra_user = get_user_model().objects.create_user(username="stu_extra", password="pass123456")
        extra_profile = StudentProfile.objects.create(
            user=extra_user,
            student_number="S999",
            enrollment_year=2024,
            major="CS",
        )
        response = self.client.post(
            "/api/enrollments/bulk_create/",
            {"course_id": self.course.id, "student_ids": [extra_profile.id, 99999]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["created_count"], 1)
        self.assertEqual(data["missing_student_ids"], [99999])

    def test_enrollment_bulk_create_bad_request(self):
        response = self.client.post("/api/enrollments/bulk_create/", {}, format="json")
        self.assertEqual(response.status_code, 400)

class ReportAndProgressApiTests(BaseApiFixture):
    def test_course_report_distribution(self):
        response = self.client.get(f"/api/courses/{self.course.id}/report/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["distribution"]["excellent"], 1)
        self.assertEqual(data["distribution"]["pass"], 1)
        self.assertEqual(data["distribution"]["pending"], 1)
        self.assertEqual(len(data["top3"]), 2)

    def test_student_progress_payload(self):
        student_profile = self.students[0][0]
        response = self.client.get(f"/api/students/{student_profile.id}/progress/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["student_number"], "S001")
        self.assertEqual(data["course_count"], 1)
        self.assertEqual(data["scored_course_count"], 1)
        self.assertIsNotNone(data["overall_average"])


    def test_enrollment_history(self):
        enrollment = self.students[0][1]
        response = self.client.get(f"/api/enrollments/{enrollment.id}/history/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["student_number"], "S001")
        self.assertGreaterEqual(len(data["classroom_history"]), 1)
        self.assertGreaterEqual(len(data["homework_history"]), 1)
