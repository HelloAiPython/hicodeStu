from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.models import Course, ScoreRule


class Command(BaseCommand):
    help = "初始化演示课程和默认评分规则（classroom/homework = 50/50）"

    def add_arguments(self, parser):
        parser.add_argument("--teacher", required=True, help="教师用户名（必须已存在）")
        parser.add_argument("--course-code", default="C001", help="课程编码")
        parser.add_argument("--course-name", default="示例课程", help="课程名称")

    def handle(self, *args, **options):
        User = get_user_model()
        teacher_name = options["teacher"]

        try:
            teacher = User.objects.get(username=teacher_name)
        except User.DoesNotExist as exc:
            raise CommandError(f"教师用户不存在: {teacher_name}") from exc

        course, _ = Course.objects.get_or_create(
            code=options["course_code"],
            defaults={"name": options["course_name"], "teacher": teacher},
        )

        ScoreRule.objects.update_or_create(
            course=course,
            name="classroom",
            defaults={"weight": 50, "is_active": True},
        )
        ScoreRule.objects.update_or_create(
            course=course,
            name="homework",
            defaults={"weight": 50, "is_active": True},
        )

        self.stdout.write(self.style.SUCCESS(f"已初始化课程与评分规则: {course.code} {course.name}"))
