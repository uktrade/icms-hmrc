# Generated by Django 2.2.17 on 2021-02-03 21:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mail", "0003_mailboxconfig_mailreadstatus"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mailreadstatus",
            name="status",
            field=models.TextField(choices=[("READ", "Read"), ("UNREAD", "Unread")], db_index=True, default="UNREAD"),
        ),
    ]
