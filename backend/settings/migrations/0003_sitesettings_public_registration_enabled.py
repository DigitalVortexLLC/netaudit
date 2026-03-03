from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("site_settings", "0002_sitesettings_slack_webhook_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="public_registration_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Allow new users to register via the public signup page.",
            ),
        ),
    ]
