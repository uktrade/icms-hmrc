# Generated by Django 2.2.23 on 2022-03-10 11:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mail', '0015_licencepayload_skip'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='licencepayload',
            name='skip',
        ),
    ]
