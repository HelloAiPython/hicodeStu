import csv

from django.db.models import Q
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from .models import (
    ClassroomScore,
    Course,
    Enrollment,
    HomeworkScore,
    ScoreAuditLog,
    ScoreRule,
    StudentProfile,
)
from .serializers import (
    ClassroomScoreSerializer,
    CourseSerializer,
    EnrollmentSerializer,
    HomeworkScoreSerializer,
    ScoreAuditLogSerializer,
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




def student_alerts_rows(profile, threshold):
    enrollments = Enrollment.objects.select_related("course", "student").filter(student=profile)
    rows = [enrollment_summary(enrollment) for enrollment in enrollments]

    pending_courses = [
        {
            "course_id": enrollment.course_id,
            "course_code": enrollment.course.code,
            "course_name": enrollment.course.name,
        }
        for enrollment, row in zip(enrollments, rows)
        if row["total_score"] is None or not (row["has_classroom"] and row["has_homework"])
    ]
    risk_courses = [
        {
            "course_id": enrollment.course_id,
            "course_code": enrollment.course.code,
            "course_name": enrollment.course.name,
            "total_score": row["total_score"],
        }
        for enrollment, row in zip(enrollments, rows)
        if row["total_score"] is not None and row["total_score"] < threshold
    ]
    risk_courses.sort(key=lambda item: item["total_score"])

    return {
        "pending_count": len(pending_courses),
        "risk_count": len(risk_courses),
        "pending_courses": pending_courses,
        "risk_courses": risk_courses,
    }


def student_alerts_board_rows(queryset, threshold, filter_mode="all"):
    results = []
    total_pending_count = 0
    total_risk_count = 0

    for profile in queryset:
        summary = student_alerts_rows(profile, threshold)
        if summary["pending_count"] == 0 and summary["risk_count"] == 0:
            continue
        if filter_mode == "risk" and summary["risk_count"] == 0:
            continue
        if filter_mode == "pending" and summary["pending_count"] == 0:
            continue

        total_pending_count += summary["pending_count"]
        total_risk_count += summary["risk_count"]
        results.append(
            {
                "student_id": profile.id,
                "student_number": profile.student_number,
                "username": profile.user.username,
                "pending_count": summary["pending_count"],
                "risk_count": summary["risk_count"],
            }
        )

    results.sort(key=lambda item: (item["risk_count"], item["pending_count"]), reverse=True)
    return {
        "results": results,
        "student_count": len(results),
        "pending_total": total_pending_count,
        "risk_total": total_risk_count,
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


def parse_bool_flag(raw_value):
    return str(raw_value).lower() in {"1", "true", "yes", "y", "on"}


def resolve_alert_filter_mode(request):
    risk_only = parse_bool_flag(request.query_params.get("risk_only"))
    pending_only = parse_bool_flag(request.query_params.get("pending_only"))
    if risk_only and not pending_only:
        return "risk"
    if pending_only and not risk_only:
        return "pending"
    return "all"


def log_score_audit(request, action, target_type, target_id=None, detail=""):
    if request.user and request.user.is_authenticated:
        ScoreAuditLog.objects.create(
            actor=request.user,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )


class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsTeacherOrStudentSelfReadOnly(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_staff:
            return True
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.is_staff:
            return True
        return request.method in permissions.SAFE_METHODS and obj.user_id == request.user.id


class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsTeacherOrStudentSelfReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("user")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def current_student_profile(self):
        if self.request.user.is_staff:
            raise PermissionDenied("教师账号请使用按学生 ID 的管理接口。")
        profile = StudentProfile.objects.select_related("user").filter(user=self.request.user).first()
        if not profile:
            raise NotFound("当前账号未绑定学生档案。")
        return profile

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        profile = self.current_student_profile()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="me/progress")
    def me_progress(self, request):
        profile = self.current_student_profile()
        payload = student_progress(profile)
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="me/alerts")
    def me_alerts(self, request):
        profile = self.current_student_profile()
        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0
        payload = student_alerts_rows(profile, threshold)
        payload.update(
            {
                "student_id": profile.id,
                "student_number": profile.student_number,
                "threshold": threshold,
            }
        )
        return Response(payload)


    @action(detail=False, methods=["get"], url_path="alerts_board", permission_classes=[IsTeacher])
    def alerts_board(self, request):
        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0

        keyword = (request.query_params.get("q") or "").strip()
        limit = parse_positive_int(request.query_params.get("limit"), 50)
        filter_mode = resolve_alert_filter_mode(request)

        queryset = self.get_queryset().select_related("user")
        if keyword:
            queryset = queryset.filter(
                Q(student_number__icontains=keyword) | Q(user__username__icontains=keyword)
            )
        queryset = queryset.order_by("id")

        board = student_alerts_board_rows(queryset, threshold, filter_mode=filter_mode)
        limited_results = board["results"][:limit]
        return Response(
            {
                "threshold": threshold,
                "keyword": keyword,
                "limit": limit,
                "filter_mode": filter_mode,
                "count": len(limited_results),
                "total_count": board["student_count"],
                "results": limited_results,
            }
        )

    @action(detail=False, methods=["get"], url_path="alerts_board_export", permission_classes=[IsTeacher])
    def alerts_board_export(self, request):
        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0

        keyword = (request.query_params.get("q") or "").strip()
        filter_mode = resolve_alert_filter_mode(request)

        queryset = self.get_queryset().select_related("user")
        if keyword:
            queryset = queryset.filter(
                Q(student_number__icontains=keyword) | Q(user__username__icontains=keyword)
            )
        queryset = queryset.order_by("id")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="students_alerts_board.csv"'
        writer = csv.writer(response)
        writer.writerow(["student_number", "username", "pending_count", "risk_count", "threshold"])

        board = student_alerts_board_rows(queryset, threshold, filter_mode=filter_mode)
        for row in board["results"]:
            writer.writerow(
                [
                    row["student_number"],
                    row["username"],
                    row["pending_count"],
                    row["risk_count"],
                    threshold,
                ]
            )

        return response

    @action(detail=False, methods=["get"], url_path="alerts_board_stats", permission_classes=[IsTeacher])
    def alerts_board_stats(self, request):
        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0

        keyword = (request.query_params.get("q") or "").strip()
        filter_mode = resolve_alert_filter_mode(request)

        queryset = self.get_queryset().select_related("user")
        if keyword:
            queryset = queryset.filter(
                Q(student_number__icontains=keyword) | Q(user__username__icontains=keyword)
            )
        queryset = queryset.order_by("id")

        board = student_alerts_board_rows(queryset, threshold, filter_mode=filter_mode)
        return Response(
            {
                "threshold": threshold,
                "keyword": keyword,
                "filter_mode": filter_mode,
                "alert_student_count": board["student_count"],
                "pending_total": board["pending_total"],
                "risk_total": board["risk_total"],
            }
        )

    @action(detail=False, methods=["get"], url_path="search", permission_classes=[IsTeacher])
    def search(self, request):
        keyword = (request.query_params.get("q") or "").strip()
        queryset = self.get_queryset()
        if keyword:
            queryset = queryset.filter(student_number__icontains=keyword)

        queryset = queryset.select_related("user")[:50]
        return Response(
            {
                "count": queryset.count(),
                "results": [
                    {
                        "id": item.id,
                        "student_number": item.student_number,
                        "major": item.major,
                        "enrollment_year": item.enrollment_year,
                        "username": item.user.username,
                    }
                    for item in queryset
                ],
            }
        )



    @action(detail=True, methods=["get"])
    def alerts_export(self, request, pk=None):
        profile = self.get_object()
        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0

        enrollments = Enrollment.objects.select_related("course", "student").filter(student=profile)
        rows = [enrollment_summary(enrollment) for enrollment in enrollments]

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="{profile.student_number}_alerts.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(["course_code", "course_name", "status", "total_score", "threshold"])

        for enrollment, row in zip(enrollments, rows):
            status = "normal"
            if row["total_score"] is None or not (row["has_classroom"] and row["has_homework"]):
                status = "pending"
            elif row["total_score"] < threshold:
                status = "risk"

            writer.writerow(
                [
                    enrollment.course.code,
                    enrollment.course.name,
                    status,
                    row["total_score"],
                    threshold,
                ]
            )

        return response

    @action(detail=True, methods=["get"])
    def alerts(self, request, pk=None):
        profile = self.get_object()
        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0

        summary = student_alerts_rows(profile, threshold)

        return Response(
            {
                "student_id": profile.id,
                "student_number": profile.student_number,
                "threshold": threshold,
                "pending_count": summary["pending_count"],
                "risk_count": summary["risk_count"],
                "pending_courses": summary["pending_courses"],
                "risk_courses": summary["risk_courses"],
            }
        )

    @action(detail=True, methods=["get"], url_path="detail_dashboard")
    def detail_dashboard(self, request, pk=None):
        profile = self.get_object()
        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0

        alerts_payload = student_alerts_rows(profile, threshold)
        progress_payload = student_progress(profile)
        return Response(
            {
                "student_id": profile.id,
                "student_number": profile.student_number,
                "threshold": threshold,
                "alerts": {
                    "pending_count": alerts_payload["pending_count"],
                    "risk_count": alerts_payload["risk_count"],
                    "pending_courses": alerts_payload["pending_courses"],
                    "risk_courses": alerts_payload["risk_courses"],
                },
                "progress": progress_payload,
            }
        )

    @action(detail=True, methods=["get"], url_path="detail_dashboard_export")
    def detail_dashboard_export(self, request, pk=None):
        profile = self.get_object()
        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0

        alerts_payload = student_alerts_rows(profile, threshold)
        progress_payload = student_progress(profile)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="{profile.student_number}_detail_dashboard.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(["student_number", profile.student_number])
        writer.writerow(["threshold", threshold])
        writer.writerow([])

        writer.writerow(["section", "metric", "value"])
        writer.writerow(["alerts", "pending_count", alerts_payload["pending_count"]])
        writer.writerow(["alerts", "risk_count", alerts_payload["risk_count"]])
        writer.writerow(["progress", "course_count", progress_payload["course_count"]])
        writer.writerow(["progress", "scored_course_count", progress_payload["scored_course_count"]])
        writer.writerow(["progress", "pending_course_count", progress_payload["pending_course_count"]])
        writer.writerow(["progress", "overall_average", progress_payload["overall_average"]])
        writer.writerow([])

        writer.writerow(["alerts_pending_courses", "course_code", "course_name"])
        for item in alerts_payload["pending_courses"]:
            writer.writerow(["pending", item["course_code"], item["course_name"]])
        writer.writerow(["alerts_risk_courses", "course_code", "course_name", "total_score"])
        for item in alerts_payload["risk_courses"]:
            writer.writerow(["risk", item["course_code"], item["course_name"], item["total_score"]])

        return response

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        profile = self.get_object()
        return Response(student_progress(profile))


    @action(detail=True, methods=["get"])
    def progress_export(self, request, pk=None):
        profile = self.get_object()
        payload = student_progress(profile)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="{profile.student_number}_progress.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            "course_code",
            "course_name",
            "total_score",
            "has_classroom",
            "has_homework",
        ])
        for row in payload["courses"]:
            writer.writerow(
                [
                    row["course_code"],
                    row["course_name"],
                    row["total_score"],
                    row["has_classroom"],
                    row["has_homework"],
                ]
            )

        return response


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsTeacher]




    @action(detail=False, methods=["get"], url_path="workload_export")
    def workload_export(self, request):
        teacher_id = request.query_params.get("teacher_id")
        queryset = Course.objects.all()
        if teacher_id and str(teacher_id).isdigit():
            queryset = queryset.filter(teacher_id=int(teacher_id))

        rows = []
        for course in queryset.order_by("id"):
            enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
            summary_rows = [enrollment_summary(enrollment) for enrollment in enrollments]
            pending_count = sum(
                1
                for row in summary_rows
                if row["total_score"] is None or not (row["has_classroom"] and row["has_homework"])
            )
            completion_rate = (
                round(((len(summary_rows) - pending_count) / len(summary_rows)) * 100, 2)
                if summary_rows
                else None
            )
            rows.append(
                {
                    "course_code": course.code,
                    "course_name": course.name,
                    "teacher_id": course.teacher_id,
                    "enrollment_count": len(summary_rows),
                    "pending_count": pending_count,
                    "completion_rate": completion_rate,
                }
            )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="workload_overview.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "course_code",
                "course_name",
                "teacher_id",
                "enrollment_count",
                "pending_count",
                "completion_rate",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["course_code"],
                    row["course_name"],
                    row["teacher_id"],
                    row["enrollment_count"],
                    row["pending_count"],
                    row["completion_rate"],
                ]
            )

        return response

    @action(detail=False, methods=["get"], url_path="workload")
    def workload(self, request):
        teacher_id = request.query_params.get("teacher_id")
        queryset = Course.objects.all()
        if teacher_id and str(teacher_id).isdigit():
            queryset = queryset.filter(teacher_id=int(teacher_id))

        results = []
        total_courses = 0
        total_enrollments = 0
        total_pending = 0

        for course in queryset.order_by("id"):
            enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
            rows = [enrollment_summary(enrollment) for enrollment in enrollments]
            pending_count = sum(
                1
                for row in rows
                if row["total_score"] is None or not (row["has_classroom"] and row["has_homework"])
            )

            total_courses += 1
            total_enrollments += len(rows)
            total_pending += pending_count

            results.append(
                {
                    "course_id": course.id,
                    "course_code": course.code,
                    "course_name": course.name,
                    "teacher_id": course.teacher_id,
                    "enrollment_count": len(rows),
                    "pending_count": pending_count,
                    "completion_rate": round(
                        ((len(rows) - pending_count) / len(rows)) * 100, 2
                    )
                    if rows
                    else None,
                }
            )

        return Response(
            {
                "course_count": total_courses,
                "enrollment_count": total_enrollments,
                "pending_count": total_pending,
                "results": results,
            }
        )

    @action(detail=False, methods=["get"], url_path="compare")
    def compare(self, request):
        course_ids = request.query_params.getlist("course_ids")
        valid_ids = [int(cid) for cid in course_ids if str(cid).isdigit()]
        if not valid_ids:
            return Response({"detail": "请提供 course_ids 参数。"}, status=400)

        courses = Course.objects.filter(id__in=valid_ids)
        results = []
        for course in courses:
            enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
            rows = [enrollment_summary(enrollment) for enrollment in enrollments]
            scored = [row["total_score"] for row in rows if row["total_score"] is not None]
            avg = round(sum(scored) / len(scored), 2) if scored else None
            results.append(
                {
                    "course_id": course.id,
                    "course_code": course.code,
                    "course_name": course.name,
                    "student_count": len(rows),
                    "scored_count": len(scored),
                    "average_score": avg,
                }
            )

        results.sort(
            key=lambda item: item["average_score"] if item["average_score"] is not None else -1,
            reverse=True,
        )
        return Response({"count": len(results), "results": results})

    @action(detail=False, methods=["get"])
    def global_overview(self, request):
        courses = Course.objects.count()
        students = StudentProfile.objects.count()
        enrollments = Enrollment.objects.count()

        classroom_scored = ClassroomScore.objects.values("enrollment_id").distinct().count()
        homework_scored = HomeworkScore.objects.values("enrollment_id").distinct().count()
        fully_scored = (
            Enrollment.objects.filter(id__in=ClassroomScore.objects.values("enrollment_id"))
            .filter(id__in=HomeworkScore.objects.values("enrollment_id"))
            .distinct()
            .count()
        )

        return Response(
            {
                "course_count": courses,
                "student_count": students,
                "enrollment_count": enrollments,
                "classroom_scored_enrollment_count": classroom_scored,
                "homework_scored_enrollment_count": homework_scored,
                "fully_scored_enrollment_count": fully_scored,
                "pending_enrollment_count": max(enrollments - fully_scored, 0),
            }
        )

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
    def action_board(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
        rows = [enrollment_summary(enrollment) for enrollment in enrollments]

        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0
        limit = parse_positive_int(request.query_params.get("limit"), 10)

        pending_rows = [
            row
            for row in rows
            if row["total_score"] is None or not (row["has_classroom"] and row["has_homework"])
        ]
        risk_rows = [
            row
            for row in rows
            if row["total_score"] is not None and row["total_score"] < threshold
        ]
        risk_rows.sort(key=lambda item: item["total_score"])

        return Response(
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "threshold": threshold,
                "pending_count": len(pending_rows),
                "risk_count": len(risk_rows),
                "pending_examples": pending_rows[:limit],
                "risk_examples": risk_rows[:limit],
            }
        )

    @action(detail=True, methods=["get"])
    def risk_list(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
        rows = [enrollment_summary(enrollment) for enrollment in enrollments]

        threshold = parse_optional_float(request.query_params.get("threshold"))
        if threshold is None:
            threshold = 60.0

        risk_rows = [
            row
            for row in rows
            if row["total_score"] is not None and row["total_score"] < threshold
        ]
        risk_rows.sort(key=lambda item: item["total_score"])  # ascending, lowest first

        page = parse_positive_int(request.query_params.get("page"), 1)
        page_size = parse_positive_int(request.query_params.get("page_size"), 20)
        total = len(risk_rows)
        start = (page - 1) * page_size
        end = start + page_size

        return Response(
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "threshold": threshold,
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": risk_rows[start:end],
            }
        )

    @action(detail=True, methods=["get"])
    def pending_list(self, request, pk=None):
        course = self.get_object()
        enrollments = Enrollment.objects.select_related("student", "course").filter(course=course)
        rows = [enrollment_summary(enrollment) for enrollment in enrollments]

        pending_rows = [
            row
            for row in rows
            if row["total_score"] is None or not (row["has_classroom"] and row["has_homework"])
        ]

        page = parse_positive_int(request.query_params.get("page"), 1)
        page_size = parse_positive_int(request.query_params.get("page_size"), 20)
        total = len(pending_rows)
        start = (page - 1) * page_size
        end = start + page_size

        return Response(
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": pending_rows[start:end],
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

    @action(detail=False, methods=["post"], url_path="bulk_create")
    def bulk_create(self, request):
        course_id = request.data.get("course_id")
        student_ids = request.data.get("student_ids", [])

        if not course_id or not str(course_id).isdigit():
            return Response({"detail": "请提供有效的 course_id。"}, status=400)
        if not isinstance(student_ids, list) or not student_ids:
            return Response({"detail": "student_ids 必须是非空数组。"}, status=400)

        valid_students = StudentProfile.objects.filter(id__in=student_ids)
        valid_student_ids = set(valid_students.values_list("id", flat=True))
        missing_student_ids = [sid for sid in student_ids if sid not in valid_student_ids]

        created = 0
        existed = 0
        for student in valid_students:
            _, is_created = Enrollment.objects.get_or_create(
                course_id=int(course_id),
                student=student,
            )
            if is_created:
                created += 1
            else:
                existed += 1

        log_score_audit(
            request,
            action="enrollment_bulk_create",
            target_type="course",
            target_id=int(course_id),
            detail=f"requested={len(student_ids)}, created={created}, existed={existed}",
        )

        return Response(
            {
                "course_id": int(course_id),
                "requested_count": len(student_ids),
                "created_count": created,
                "existed_count": existed,
                "missing_student_ids": missing_student_ids,
            }
        )

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

    @action(detail=False, methods=["post"], url_path="bulk_create")
    def bulk_create(self, request):
        records = request.data.get("records", [])
        if not isinstance(records, list) or not records:
            return Response({"detail": "records 必须是非空数组。"}, status=400)

        created = 0
        skipped = 0
        for item in records:
            enrollment_id = item.get("enrollment")
            if not enrollment_id:
                skipped += 1
                continue
            ClassroomScore.objects.create(
                enrollment_id=enrollment_id,
                attentive=item.get("attentive", 0),
                participation=item.get("participation", 0),
                exercise_completion=item.get("exercise_completion", 0),
                note=item.get("note", ""),
            )
            created += 1

        log_score_audit(
            request,
            action="classroom_score_bulk_create",
            target_type="classroom_score",
            detail=f"created={created}, skipped={skipped}",
        )

        return Response({"created_count": created, "skipped_count": skipped})


class HomeworkScoreViewSet(viewsets.ModelViewSet):
    queryset = HomeworkScore.objects.select_related("enrollment")
    serializer_class = HomeworkScoreSerializer
    permission_classes = [IsTeacher]

    @action(detail=False, methods=["post"], url_path="bulk_create")
    def bulk_create(self, request):
        records = request.data.get("records", [])
        if not isinstance(records, list) or not records:
            return Response({"detail": "records 必须是非空数组。"}, status=400)

        created = 0
        skipped = 0
        for item in records:
            enrollment_id = item.get("enrollment")
            if not enrollment_id:
                skipped += 1
                continue
            HomeworkScore.objects.create(
                enrollment_id=enrollment_id,
                completion=item.get("completion", 0),
                accuracy=item.get("accuracy", 0),
                correction=item.get("correction", 0),
                note=item.get("note", ""),
            )
            created += 1

        log_score_audit(
            request,
            action="homework_score_bulk_create",
            target_type="homework_score",
            detail=f"created={created}, skipped={skipped}",
        )

        return Response({"created_count": created, "skipped_count": skipped})


class ScoreRuleViewSet(viewsets.ModelViewSet):
    queryset = ScoreRule.objects.select_related("course")
    serializer_class = ScoreRuleSerializer
    permission_classes = [IsTeacher]

    @action(detail=False, methods=["get"], url_path="validate")
    def validate_weights(self, request):
        course_id = request.query_params.get("course_id")
        if not course_id or not course_id.isdigit():
            return Response({"detail": "请提供 course_id。"}, status=400)

        rules = ScoreRule.objects.filter(course_id=int(course_id), is_active=True)
        total_weight = round(sum(float(rule.weight) for rule in rules), 2)
        return Response(
            {
                "course_id": int(course_id),
                "active_rule_count": rules.count(),
                "total_weight": total_weight,
                "is_valid": total_weight == 100.0,
            }
        )


    @action(detail=False, methods=["get"], url_path="audit")
    def audit_weights(self, request):
        result = []
        courses = Course.objects.all().order_by("id")
        for course in courses:
            rules = ScoreRule.objects.filter(course=course, is_active=True)
            total_weight = round(sum(float(rule.weight) for rule in rules), 2)
            result.append(
                {
                    "course_id": course.id,
                    "course_code": course.code,
                    "course_name": course.name,
                    "active_rule_count": rules.count(),
                    "total_weight": total_weight,
                    "is_valid": total_weight == 100.0,
                }
            )

        invalid_count = sum(1 for item in result if not item["is_valid"])
        return Response(
            {
                "course_count": len(result),
                "invalid_count": invalid_count,
                "results": result,
            }
        )

    @action(detail=False, methods=["post"], url_path="normalize")
    def normalize_weights(self, request):
        course_id = request.data.get("course_id")
        if not course_id or not str(course_id).isdigit():
            return Response({"detail": "请提供 course_id。"}, status=400)

        rules = list(ScoreRule.objects.filter(course_id=int(course_id), is_active=True).order_by("id"))
        if not rules:
            return Response({"detail": "没有可归一化的启用规则。"}, status=400)

        current_total = sum(float(rule.weight) for rule in rules)
        if current_total <= 0:
            equal_weight = round(100.0 / len(rules), 2)
            for rule in rules:
                rule.weight = equal_weight
                rule.save(update_fields=["weight"])
        else:
            scaled = []
            for rule in rules:
                value = round(float(rule.weight) * 100.0 / current_total, 2)
                scaled.append(value)

            diff = round(100.0 - sum(scaled), 2)
            scaled[-1] = round(scaled[-1] + diff, 2)

            for rule, value in zip(rules, scaled):
                rule.weight = value
                rule.save(update_fields=["weight"])

        total_weight = round(sum(float(rule.weight) for rule in rules), 2)
        log_score_audit(
            request,
            action="score_rule_normalize",
            target_type="course",
            target_id=int(course_id),
            detail=f"active_rule_count={len(rules)}, total_weight={total_weight}",
        )
        return Response(
            {
                "course_id": int(course_id),
                "active_rule_count": len(rules),
                "total_weight": total_weight,
                "is_valid": total_weight == 100.0,
            }
        )


class ScoreAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScoreAuditLog.objects.select_related("actor")
    serializer_class = ScoreAuditLogSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("actor")
        action_name = (self.request.query_params.get("action") or "").strip()
        target_type = (self.request.query_params.get("target_type") or "").strip()
        actor_username = (self.request.query_params.get("actor_username") or "").strip()
        target_id = (self.request.query_params.get("target_id") or "").strip()
        date_from = parse_date((self.request.query_params.get("date_from") or "").strip())
        date_to = parse_date((self.request.query_params.get("date_to") or "").strip())

        if action_name:
            queryset = queryset.filter(action=action_name)
        if target_type:
            queryset = queryset.filter(target_type=target_type)
        if actor_username:
            queryset = queryset.filter(actor__username__icontains=actor_username)
        if target_id.isdigit():
            queryset = queryset.filter(target_id=int(target_id))
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        return queryset

    def list(self, request, *args, **kwargs):
        limit = parse_positive_int(request.query_params.get("limit"), 50)
        queryset = self.get_queryset().order_by("-id")
        page = queryset[:limit]
        serializer = self.get_serializer(page, many=True)
        return Response(
            {
                "count": len(serializer.data),
                "limit": limit,
                "results": serializer.data,
            }
        )

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        queryset = self.get_queryset().order_by("-id")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="score_audit_logs.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["id", "actor_username", "action", "target_type", "target_id", "detail", "created_at"]
        )
        for item in queryset:
            writer.writerow(
                [
                    item.id,
                    item.actor.username,
                    item.action,
                    item.target_type,
                    item.target_id or "",
                    item.detail,
                    item.created_at.isoformat(),
                ]
            )
        return response

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        queryset = self.get_queryset()
        action_counts = {}
        target_type_counts = {}
        for item in queryset:
            action_counts[item.action] = action_counts.get(item.action, 0) + 1
            target_type_counts[item.target_type] = target_type_counts.get(item.target_type, 0) + 1

        top_actions = sorted(action_counts.items(), key=lambda pair: pair[1], reverse=True)
        top_targets = sorted(target_type_counts.items(), key=lambda pair: pair[1], reverse=True)
        return Response(
            {
                "count": queryset.count(),
                "action_breakdown": [
                    {"action": action, "count": count} for action, count in top_actions
                ],
                "target_type_breakdown": [
                    {"target_type": target_type, "count": count}
                    for target_type, count in top_targets
                ],
            }
        )

    @action(detail=False, methods=["post"], url_path="purge")
    def purge(self, request):
        before_date_raw = (request.data.get("before_date") or "").strip()
        before_date = parse_date(before_date_raw)
        if not before_date:
            return Response({"detail": "请提供有效的 before_date（YYYY-MM-DD）。"}, status=400)

        dry_run = parse_bool_flag(request.data.get("dry_run", 1))
        max_delete = parse_positive_int(request.data.get("max_delete"), 5000)
        queryset = ScoreAuditLog.objects.filter(created_at__date__lt=before_date)
        to_delete_count = queryset.count()
        if to_delete_count > max_delete:
            return Response(
                {
                    "detail": "待删除日志数超过 max_delete 限制，请缩小时间范围或提高 max_delete。",
                    "before_date": before_date_raw,
                    "max_delete": max_delete,
                    "would_delete_count": to_delete_count,
                },
                status=400,
            )

        if dry_run:
            return Response(
                {
                    "before_date": before_date_raw,
                    "dry_run": True,
                    "max_delete": max_delete,
                    "would_delete_count": to_delete_count,
                }
            )

        if (request.data.get("confirm") or "").strip().upper() != "DELETE":
            return Response(
                {"detail": "执行删除请提供 confirm=DELETE。", "before_date": before_date_raw},
                status=400,
            )

        deleted_count, _ = queryset.delete()
        log_score_audit(
            request,
            action="score_audit_purge",
            target_type="score_audit_log",
            detail=f"before_date={before_date_raw}, deleted_count={deleted_count}",
        )
        return Response(
            {
                "before_date": before_date_raw,
                "dry_run": False,
                "max_delete": max_delete,
                "deleted_count": deleted_count,
            }
        )
