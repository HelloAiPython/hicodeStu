from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("student_number", models.CharField(max_length=32, unique=True)),
                ("enrollment_year", models.PositiveIntegerField()),
                ("major", models.CharField(blank=True, max_length=128)),
                (
                    "user",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128)),
                ("code", models.CharField(max_length=32, unique=True)),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="courses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enrolled_at", models.DateField(auto_now_add=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.course")),
                (
                    "student",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.studentprofile"),
                ),
            ],
            options={"unique_together": {("student", "course")}},
        ),
        migrations.CreateModel(
            name="ScoreRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64)),
                ("weight", models.DecimalField(decimal_places=2, max_digits=5)),
                ("is_active", models.BooleanField(default=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.course")),
            ],
            options={"unique_together": {("course", "name")}},
        ),
        migrations.CreateModel(
            name="HomeworkScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("completion", models.PositiveSmallIntegerField(default=0)),
                ("accuracy", models.PositiveSmallIntegerField(default=0)),
                ("correction", models.PositiveSmallIntegerField(default=0)),
                ("recorded_at", models.DateField(auto_now_add=True)),
                ("note", models.TextField(blank=True)),
                (
                    "enrollment",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.enrollment"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ClassroomScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attentive", models.PositiveSmallIntegerField(default=0)),
                ("participation", models.PositiveSmallIntegerField(default=0)),
                ("exercise_completion", models.PositiveSmallIntegerField(default=0)),
                ("recorded_at", models.DateField(auto_now_add=True)),
                ("note", models.TextField(blank=True)),
                (
                    "enrollment",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.enrollment"),
                ),
            ],
        ),
    ]
