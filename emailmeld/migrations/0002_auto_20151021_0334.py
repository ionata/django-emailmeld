# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emailmeld', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailmeldmodel',
            name='email_type',
            field=models.CharField(default='MARKDOWN', max_length=10, choices=[('txt', 'Text'), ('html', 'HTML'), ('md', 'Markdown')]),
        ),
    ]
