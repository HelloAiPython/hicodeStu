from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    ClassroomScore,
    Course,
    Enrollment,
    HomeworkScore,
    ScoreRule,
    StudentProfile,
)

User = get_user_model()


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ["id", "user", "student_number", "enrollment_year", "major"]


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "name", "code", "teacher"]


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ["id", "student", "course", "enrolled_at"]


class ClassroomScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassroomScore
        fields = [
            "id",
            "enrollment",
            "attentive",
            "participation",
            "exercise_completion",
            "recorded_at",
            "note",
        ]

    def validate(self, attrs):
        for field in ["attentive", "participation", "exercise_completion"]:
            value = attrs.get(field)
            if value is not None and not 0 <= value <= 100:
                raise serializers.ValidationError({field: "分数需在 0 到 100 之间。"})
        return attrs


class HomeworkScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeworkScore
        fields = [
            "id",
            "enrollment",
            "completion",
            "accuracy",
            "correction",
            "recorded_at",
            "note",
        ]

    def validate(self, attrs):
        for field in ["completion", "accuracy", "correction"]:
            value = attrs.get(field)
            if value is not None and not 0 <= value <= 100:
                raise serializers.ValidationError({field: "分数需在 0 到 100 之间。"})
        return attrs


class ScoreRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreRule
        fields = ["id", "course", "name", "weight", "is_active"]

    def validate_weight(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("权重需在 0 到 100 之间。")
        return value
