# Generated by Django 2.2.24 on 2021-07-02 15:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("mail", "0012_auto_20210520_1344"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="goodidmapping",
            unique_together=set(),
        ),
    ]
