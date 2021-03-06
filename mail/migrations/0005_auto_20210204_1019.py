# Generated by Django 2.2.17 on 2021-02-04 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mail", "0004_auto_20210203_2105"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mailreadstatus",
            name="status",
            field=models.TextField(
                choices=[("READ", "Read"), ("UNREAD", "Unread"), ("UNPROCESSABLE", "Unprocessable")],
                db_index=True,
                default="UNREAD",
            ),
        ),
    ]
