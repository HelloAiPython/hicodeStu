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


def enrollment_summary(enrollment):
    classroom_latest = (
        ClassroomScore.objects.filter(enrollment=enrollment)
        .order_by("-recorded_at", "-id")
        .first()
    )
    homework_latest = (
        HomeworkScore.objects.filter(enrollment=enrollment).order_by("-recorded_at", "-id").first()
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


class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return request.user and request.user.is_authenticated and request.user.is_staff


class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsTeacher]


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsTeacher]

    @action(detail=True, methods=["get"])
    def leaderboard(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
        rows = [enrollment_summary(enrollment) for enrollment in enrollments]
        rows.sort(key=lambda item: item["total_score"] if item["total_score"] is not None else -1, reverse=True)

        for index, row in enumerate(rows, start=1):
            row["rank"] = index if row["total_score"] is not None else None

        return Response(
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "count": len(rows),
                "results": rows,
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
