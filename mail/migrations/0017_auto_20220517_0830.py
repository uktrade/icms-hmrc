# Generated by Django 2.2.27 on 2022-05-17 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mail", "0016_remove_licencepayload_skip"),
    ]

    operations = [
        migrations.AlterField(
            model_name="licencedata",
            name="source",
            field=models.CharField(
                choices=[("SPIRE", "SPIRE"), ("LITE", "LITE"), ("HMRC", "HMRC"), ("ICMS", "ICMS")], max_length=10
            ),
        ),
    ]
