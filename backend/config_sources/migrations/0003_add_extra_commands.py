from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("config_sources", "0002_configsource_sshconfigsource"),
    ]

    operations = [
        migrations.AddField(
            model_name="netmikodevicetype",
            name="extra_commands",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="sshconfigsource",
            name="extra_commands",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
