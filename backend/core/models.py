from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    student_number = models.CharField(max_length=32, unique=True)
    enrollment_year = models.PositiveIntegerField()
    major = models.CharField(max_length=128, blank=True)

    def __str__(self) -> str:
        return f"{self.student_number}"


class Course(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32, unique=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="courses"
    )

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


class Enrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")


class ScoreRule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("course", "name")

    def __str__(self) -> str:
        return f"{self.course.code} {self.name}"


class ClassroomScore(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    attentive = models.PositiveSmallIntegerField(default=0)
    participation = models.PositiveSmallIntegerField(default=0)
    exercise_completion = models.PositiveSmallIntegerField(default=0)
    recorded_at = models.DateField(auto_now_add=True)
    note = models.TextField(blank=True)


class HomeworkScore(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    completion = models.PositiveSmallIntegerField(default=0)
    accuracy = models.PositiveSmallIntegerField(default=0)
    correction = models.PositiveSmallIntegerField(default=0)
    recorded_at = models.DateField(auto_now_add=True)
    note = models.TextField(blank=True)


class ScoreAuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="score_audit_logs"
    )
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-id",)
        indexes = [
            models.Index(fields=["created_at"], name="score_audit_created_idx"),
            models.Index(fields=["action", "created_at"], name="score_audit_action_idx"),
            models.Index(fields=["target_type", "target_id"], name="score_audit_target_idx"),
            models.Index(fields=["actor", "created_at"], name="score_audit_actor_idx"),
        ]
