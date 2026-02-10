import csv

from django.http import HttpResponse
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    ClassroomScore,
    Course,
    Enrollment,
    HomeworkScore,
    ScoreRule,
    StudentProfile,
)
from .serializers import (
    ClassroomScoreSerializer,
    CourseSerializer,
    EnrollmentSerializer,
    HomeworkScoreSerializer,
    ScoreRuleSerializer,
    StudentProfileSerializer,
)


def average_score(score, fields):
    if not score:
        return None
    values = [getattr(score, field) for field in fields]
    return round(sum(values) / len(values), 2)


def resolve_weights(course):
    rule_map = {
        rule.name.lower(): float(rule.weight)
        for rule in ScoreRule.objects.filter(course=course, is_active=True)
    }
    classroom_weight = rule_map.get("classroom", 50.0)
    homework_weight = rule_map.get("homework", 50.0)
    return classroom_weight, homework_weight


def score_band(value):
    if value is None:
        return "pending"
    if value >= 90:
        return "excellent"
    if value >= 80:
        return "good"
    if value >= 60:
        return "pass"
    return "fail"


def enrollment_summary(enrollment):
    classroom_latest = (
        ClassroomScore.objects.filter(enrollment=enrollment)
        .order_by("-recorded_at", "-id")
        .first()
    )
    homework_latest = (
        HomeworkScore.objects.filter(enrollment=enrollment)
        .order_by("-recorded_at", "-id")
        .first()
    )

    classroom_score = average_score(
        classroom_latest, ["attentive", "participation", "exercise_completion"]
    )
    homework_score = average_score(homework_latest, ["completion", "accuracy", "correction"])

    classroom_weight, homework_weight = resolve_weights(enrollment.course)
    weight_total = classroom_weight + homework_weight

    total_score = None
    if classroom_score is not None and homework_score is not None and weight_total > 0:
        total_score = round(
            (classroom_score * classroom_weight + homework_score * homework_weight)
            / weight_total,
            2,
        )

    return {
        "enrollment_id": enrollment.id,
        "student_id": enrollment.student_id,
        "student_number": enrollment.student.student_number,
        "classroom_score": classroom_score,
        "homework_score": homework_score,
        "classroom_weight": classroom_weight,
        "homework_weight": homework_weight,
        "total_score": total_score,
        "has_classroom": classroom_latest is not None,
        "has_homework": homework_latest is not None,
    }


def student_progress(profile):
    enrollments = Enrollment.objects.select_related("course", "student").filter(student=profile)
    details = []
    scores = []

    for enrollment in enrollments:
        summary = enrollment_summary(enrollment)
        details.append(
            {
                "course_id": enrollment.course_id,
                "course_code": enrollment.course.code,
                "course_name": enrollment.course.name,
                "total_score": summary["total_score"],
                "has_classroom": summary["has_classroom"],
                "has_homework": summary["has_homework"],
            }
        )
        if summary["total_score"] is not None:
            scores.append(summary["total_score"])

    overall_average = round(sum(scores) / len(scores), 2) if scores else None
    pending_count = len(details) - len(scores)

    return {
        "student_id": profile.id,
        "student_number": profile.student_number,
        "course_count": len(details),
        "scored_course_count": len(scores),
        "pending_course_count": pending_count,
        "overall_average": overall_average,
        "courses": details,
    }




def enrollment_history(enrollment):
    classroom_items = list(
        ClassroomScore.objects.filter(enrollment=enrollment)
        .order_by("recorded_at", "id")
        .values("recorded_at", "attentive", "participation", "exercise_completion")
    )
    homework_items = list(
        HomeworkScore.objects.filter(enrollment=enrollment)
        .order_by("recorded_at", "id")
        .values("recorded_at", "completion", "accuracy", "correction")
    )

    classroom_avg = [
        {
            "recorded_at": str(item["recorded_at"]),
            "score": round(
                (item["attentive"] + item["participation"] + item["exercise_completion"]) / 3,
                2,
            ),
        }
        for item in classroom_items
    ]
    homework_avg = [
        {
            "recorded_at": str(item["recorded_at"]),
            "score": round((item["completion"] + item["accuracy"] + item["correction"]) / 3, 2),
        }
        for item in homework_items
    ]

    return {
        "enrollment_id": enrollment.id,
        "student_number": enrollment.student.student_number,
        "course_code": enrollment.course.code,
        "classroom_history": classroom_avg,
        "homework_history": homework_avg,
    }

def parse_optional_float(raw_value):
    if raw_value is None or raw_value == "":
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def parse_positive_int(raw_value, default):
    if raw_value is None or raw_value == "":
        return default
    if not str(raw_value).isdigit():
        return default
    value = int(raw_value)
    return value if value > 0 else default


class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return request.user and request.user.is_authenticated and request.user.is_staff


class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsTeacher]

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        profile = self.get_object()
        return Response(student_progress(profile))


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsTeacher]

    @action(detail=True, methods=["get"])
    def overview(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
        summaries = [enrollment_summary(enrollment) for enrollment in enrollments]

        with_total = [item["total_score"] for item in summaries if item["total_score"] is not None]
        course_average = round(sum(with_total) / len(with_total), 2) if with_total else None

        return Response(
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "student_count": len(summaries),
                "scored_count": len(with_total),
                "pending_count": len(summaries) - len(with_total),
                "course_average": course_average,
            }
        )

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
        rows = [enrollment_summary(enrollment) for enrollment in enrollments]

        distribution = {
            "excellent": 0,
            "good": 0,
            "pass": 0,
            "fail": 0,
            "pending": 0,
        }
        for row in rows:
            distribution[score_band(row["total_score"])] += 1

        ranked = [row for row in rows if row["total_score"] is not None]
        ranked.sort(key=lambda item: item["total_score"], reverse=True)

        return Response(
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "distribution": distribution,
                "top3": ranked[:3],
                "pending_count": distribution["pending"],
            }
        )

    @action(detail=True, methods=["get"])
    def report_export(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
        rows = [enrollment_summary(enrollment) for enrollment in enrollments]
        rows.sort(
            key=lambda item: item["total_score"] if item["total_score"] is not None else -1,
            reverse=True,
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{course.code}_report.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "student_number",
                "classroom_score",
                "homework_score",
                "total_score",
                "band",
                "has_classroom",
                "has_homework",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["student_number"],
                    row["classroom_score"],
                    row["homework_score"],
                    row["total_score"],
                    score_band(row["total_score"]),
                    row["has_classroom"],
                    row["has_homework"],
                ]
            )
        return response

    @action(detail=True, methods=["get"])
    def leaderboard_export(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
        rows = [enrollment_summary(enrollment) for enrollment in enrollments]
        rows.sort(
            key=lambda item: item["total_score"] if item["total_score"] is not None else -1,
            reverse=True,
        )

        for index, row in enumerate(rows, start=1):
            row["rank"] = index if row["total_score"] is not None else None

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="{course.code}_leaderboard.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(["rank", "student_number", "classroom_score", "homework_score", "total_score"])
        for row in rows:
            writer.writerow(
                [
                    row["rank"],
                    row["student_number"],
                    row["classroom_score"],
                    row["homework_score"],
                    row["total_score"],
                ]
            )
        return response

    @action(detail=True, methods=["get"])
    def leaderboard(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
        rows = [enrollment_summary(enrollment) for enrollment in enrollments]

        only_scored = request.query_params.get("only_scored") == "1"
        student_number = request.query_params.get("student_number")
        min_score = parse_optional_float(request.query_params.get("min_score"))
        limit = request.query_params.get("limit")
        page = parse_positive_int(request.query_params.get("page"), 1)
        page_size = parse_positive_int(request.query_params.get("page_size"), 20)

        if only_scored:
            rows = [row for row in rows if row["total_score"] is not None]
        if student_number:
            rows = [row for row in rows if student_number in row["student_number"]]
        if min_score is not None:
            rows = [
                row
                for row in rows
                if row["total_score"] is not None and row["total_score"] >= min_score
            ]

        rows.sort(
            key=lambda item: item["total_score"] if item["total_score"] is not None else -1,
            reverse=True,
        )

        for index, row in enumerate(rows, start=1):
            row["rank"] = index if row["total_score"] is not None else None

        if limit and limit.isdigit():
            rows = rows[: int(limit)]

        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        paged_rows = rows[start:end]

        return Response(
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "count": total,
                "page": page,
                "page_size": page_size,
                "filters": {
                    "only_scored": only_scored,
                    "student_number": student_number,
                    "min_score": min_score,
                    "limit": int(limit) if limit and limit.isdigit() else None,
                },
                "results": paged_rows,
            }
        )


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related("student", "course")
    serializer_class = EnrollmentSerializer
    permission_classes = [IsTeacher]

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        enrollment = self.get_object()
        return Response(enrollment_summary(enrollment))

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        enrollment = self.get_object()
        return Response(enrollment_history(enrollment))


class ClassroomScoreViewSet(viewsets.ModelViewSet):
    queryset = ClassroomScore.objects.select_related("enrollment")
    serializer_class = ClassroomScoreSerializer
    permission_classes = [IsTeacher]


class HomeworkScoreViewSet(viewsets.ModelViewSet):
    queryset = HomeworkScore.objects.select_related("enrollment")
    serializer_class = HomeworkScoreSerializer
    permission_classes = [IsTeacher]


class ScoreRuleViewSet(viewsets.ModelViewSet):
    queryset = ScoreRule.objects.select_related("course")
    serializer_class = ScoreRuleSerializer
    permission_classes = [IsTeacher]
