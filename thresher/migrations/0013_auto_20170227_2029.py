# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-27 20:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thresher', '0012_auto_20170226_1938'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='pybossa_created',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='pybossa_owner_id',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='pybossa_secret_key',
            field=models.CharField(blank=True, default=b'', max_length=36),
        ),
        migrations.AddField(
            model_name='project',
            name='pybossa_url',
            field=models.URLField(blank=True, default=b''),
        ),
    ]