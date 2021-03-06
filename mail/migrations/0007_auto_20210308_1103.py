# Generated by Django 2.2.19 on 2021-03-08 11:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mail", "0006_delete_licenceupdate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mail",
            name="extract_type",
            field=models.CharField(
                choices=[
                    ("usage_update", "Usage update"),
                    ("usage_reply", "Usage Reply"),
                    ("licence_reply", "Licence Reply"),
                    ("licence_data", "Licence Data"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
