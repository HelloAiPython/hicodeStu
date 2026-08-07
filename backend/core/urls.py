from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClassroomScoreViewSet,
    CourseViewSet,
    EnrollmentViewSet,
    HomeworkScoreViewSet,
    ScoreAuditLogViewSet,
    ScoreRuleViewSet,
    StudentProfileViewSet,
)

router = DefaultRouter()
router.register("students", StudentProfileViewSet)
router.register("courses", CourseViewSet)
router.register("enrollments", EnrollmentViewSet)
router.register("classroom-scores", ClassroomScoreViewSet)
router.register("homework-scores", HomeworkScoreViewSet)
router.register("score-rules", ScoreRuleViewSet)
router.register("score-audit-logs", ScoreAuditLogViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
