# Generated by Django 5.0 on 2023-12-25 04:05

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nominate", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportRecipient",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("report_name", models.CharField(max_length=200)),
                ("recipient_name", models.CharField(max_length=200)),
                ("recipient_email", models.CharField(max_length=200)),
            ],
        ),
        migrations.AlterModelOptions(
            name="election",
            options={
                "permissions": [
                    ("nominate", "Can nominate in WSFS elections"),
                    ("preview_nominate", "Can nominate during the preview phase"),
                    ("vote", "Can vote in WSFS elections"),
                    (
                        "preview_vote",
                        "Can vote in WSFS elections during the preview phase",
                    ),
                    ("report", "Can access reports for this election"),
                ]
            },
        ),
    ]