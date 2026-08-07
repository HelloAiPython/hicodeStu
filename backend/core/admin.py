from django.contrib import admin

from .models import (
    ClassroomScore,
    Course,
    Enrollment,
    HomeworkScore,
    ScoreAuditLog,
    ScoreRule,
    StudentProfile,
)

admin.site.register(StudentProfile)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(ClassroomScore)
admin.site.register(HomeworkScore)
admin.site.register(ScoreRule)
admin.site.register(ScoreAuditLog)
