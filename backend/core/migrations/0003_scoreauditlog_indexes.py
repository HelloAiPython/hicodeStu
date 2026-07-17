from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_scoreauditlog"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="scoreauditlog",
            index=models.Index(fields=["created_at"], name="score_audit_created_idx"),
        ),
        migrations.AddIndex(
            model_name="scoreauditlog",
            index=models.Index(fields=["action", "created_at"], name="score_audit_action_idx"),
        ),
        migrations.AddIndex(
            model_name="scoreauditlog",
            index=models.Index(fields=["target_type", "target_id"], name="score_audit_target_idx"),
        ),
        migrations.AddIndex(
            model_name="scoreauditlog",
            index=models.Index(fields=["actor", "created_at"], name="score_audit_actor_idx"),
        ),
    ]
