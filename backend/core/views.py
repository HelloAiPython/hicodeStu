from rest_framework import permissions, viewsets

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


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related("student", "course")
    serializer_class = EnrollmentSerializer
    permission_classes = [IsTeacher]


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
