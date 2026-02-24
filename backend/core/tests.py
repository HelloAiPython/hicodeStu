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

    def test_course_workload_export(self):
        response = self.client.get("/api/courses/workload_export/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment; filename=", response["Content-Disposition"])

    def test_course_workload(self):
        response = self.client.get("/api/courses/workload/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course_count"], 1)
        self.assertEqual(data["enrollment_count"], 3)
        self.assertEqual(data["pending_count"], 1)
        self.assertEqual(data["results"][0]["pending_count"], 1)

    def test_course_workload_with_teacher_filter(self):
        response = self.client.get(f"/api/courses/workload/?teacher_id={self.teacher.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course_count"], 1)

    def test_course_compare(self):
        extra_course = Course.objects.create(code="C002", name="英语", teacher=self.teacher)
        ScoreRule.objects.create(course=extra_course, name="classroom", weight=Decimal("50.00"))
        ScoreRule.objects.create(course=extra_course, name="homework", weight=Decimal("50.00"))

        profile = self.students[0][0]
        enrollment = Enrollment.objects.create(student=profile, course=extra_course)
        ClassroomScore.objects.create(enrollment=enrollment, attentive=80, participation=80, exercise_completion=80)
        HomeworkScore.objects.create(enrollment=enrollment, completion=80, accuracy=80, correction=80)

        response = self.client.get(
            f"/api/courses/compare/?course_ids={self.course.id}&course_ids={extra_course.id}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertIn("average_score", data["results"][0])

    def test_course_compare_missing_ids(self):
        response = self.client.get("/api/courses/compare/")
        self.assertEqual(response.status_code, 400)

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

    def test_student_search(self):
        response = self.client.get("/api/students/search/?q=S00")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 3)

    def test_student_search_no_match(self):
        response = self.client.get("/api/students/search/?q=NOT_FOUND")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(len(data["results"]), 0)

    def test_student_alerts_board(self):
        response = self.client.get("/api/students/alerts_board/?threshold=80")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["limit"], 50)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["student_number"], "S002")
        self.assertEqual(data["results"][0]["risk_count"], 1)
        self.assertEqual(data["results"][1]["student_number"], "S003")
        self.assertEqual(data["results"][1]["pending_count"], 1)

    def test_student_alerts_board_keyword_and_limit(self):
        response = self.client.get("/api/students/alerts_board/?threshold=80&q=stu&limit=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["keyword"], "stu")
        self.assertEqual(data["limit"], 1)
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["student_number"], "S002")

    def test_student_alerts_board_stats(self):
        response = self.client.get("/api/students/alerts_board_stats/?threshold=80")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["alert_student_count"], 2)
        self.assertEqual(data["pending_total"], 1)
        self.assertEqual(data["risk_total"], 1)

    def test_student_alerts_board_stats_with_keyword(self):
        response = self.client.get("/api/students/alerts_board_stats/?threshold=80&q=S003")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["alert_student_count"], 1)
        self.assertEqual(data["pending_total"], 1)
        self.assertEqual(data["risk_total"], 0)

    def test_student_alerts_board_risk_only(self):
        response = self.client.get("/api/students/alerts_board/?threshold=80&risk_only=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["filter_mode"], "risk")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], 1)
        self.assertEqual(data["results"][0]["student_number"], "S002")

    def test_student_alerts_board_stats_risk_only(self):
        response = self.client.get("/api/students/alerts_board_stats/?threshold=80&risk_only=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["filter_mode"], "risk")
        self.assertEqual(data["alert_student_count"], 1)
        self.assertEqual(data["pending_total"], 0)
        self.assertEqual(data["risk_total"], 1)

    def test_student_alerts_board_export_risk_only(self):
        response = self.client.get("/api/students/alerts_board_export/?threshold=80&risk_only=1")
        self.assertEqual(response.status_code, 200)
        lines = response.content.decode("utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[1].startswith("S002,"))

    def test_student_alerts_board_pending_only(self):
        response = self.client.get("/api/students/alerts_board/?threshold=80&pending_only=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["filter_mode"], "pending")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["student_number"], "S003")

    def test_student_alerts_board_stats_pending_only(self):
        response = self.client.get("/api/students/alerts_board_stats/?threshold=80&pending_only=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["filter_mode"], "pending")
        self.assertEqual(data["alert_student_count"], 1)
        self.assertEqual(data["pending_total"], 1)
        self.assertEqual(data["risk_total"], 0)

    def test_student_alerts_board_export_pending_only(self):
        response = self.client.get("/api/students/alerts_board_export/?threshold=80&pending_only=1")
        self.assertEqual(response.status_code, 200)
        lines = response.content.decode("utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[1].startswith("S003,"))

    def test_student_alerts_board_export_csv(self):
        response = self.client.get("/api/students/alerts_board_export/?threshold=80")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        lines = response.content.decode("utf-8").strip().splitlines()
        self.assertGreaterEqual(len(lines), 3)
        self.assertIn("student_number,username,pending_count,risk_count,threshold", lines[0])

    def test_student_alerts_board_export_with_keyword(self):
        response = self.client.get("/api/students/alerts_board_export/?threshold=80&q=S003")
        self.assertEqual(response.status_code, 200)
        lines = response.content.decode("utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[1].startswith("S003,"))

    def test_classroom_score_bulk_create(self):
        enrollment = self.students[2][1]
        response = self.client.post(
            "/api/classroom-scores/bulk_create/",
            {
                "records": [
                    {
                        "enrollment": enrollment.id,
                        "attentive": 88,
                        "participation": 86,
                        "exercise_completion": 90,
                    },
                    {"attentive": 10},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["created_count"], 1)
        self.assertEqual(data["skipped_count"], 1)

    def test_homework_score_bulk_create(self):
        enrollment = self.students[2][1]
        response = self.client.post(
            "/api/homework-scores/bulk_create/",
            {
                "records": [
                    {"enrollment": enrollment.id, "completion": 87, "accuracy": 85, "correction": 90},
                    {"accuracy": 10},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["created_count"], 1)
        self.assertEqual(data["skipped_count"], 1)

    def test_course_action_board(self):
        response = self.client.get(f"/api/courses/{self.course.id}/action_board/?threshold=80&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pending_count"], 1)
        self.assertEqual(data["risk_count"], 1)
        self.assertEqual(len(data["pending_examples"]), 1)
        self.assertEqual(len(data["risk_examples"]), 1)

    def test_course_risk_list(self):
        response = self.client.get(f"/api/courses/{self.course.id}/risk_list/?threshold=80")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["student_number"], "S002")

    def test_course_pending_list(self):
        response = self.client.get(f"/api/courses/{self.course.id}/pending_list/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["student_number"], "S003")

class ReportAndProgressApiTests(BaseApiFixture):
    def test_course_report_distribution(self):
        response = self.client.get(f"/api/courses/{self.course.id}/report/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["distribution"]["excellent"], 1)
        self.assertEqual(data["distribution"]["pass"], 1)
        self.assertEqual(data["distribution"]["pending"], 1)
        self.assertEqual(len(data["top3"]), 2)

    def test_student_alerts_export_csv(self):
        student_profile = self.students[2][0]
        response = self.client.get(
            f"/api/students/{student_profile.id}/alerts_export/?threshold=80"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment; filename=", response["Content-Disposition"])

    def test_student_alerts(self):
        student_profile = self.students[2][0]
        response = self.client.get(
            f"/api/students/{student_profile.id}/alerts/?threshold=80"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pending_count"], 1)
        self.assertEqual(data["risk_count"], 0)

    def test_student_progress_export_csv(self):
        student_profile = self.students[0][0]
        response = self.client.get(f"/api/students/{student_profile.id}/progress_export/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment; filename=", response["Content-Disposition"])

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
