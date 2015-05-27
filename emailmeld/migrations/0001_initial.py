# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmailMeldModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email_type', models.CharField(default=b'MARKDOWN', max_length=10, choices=[(b'txt', b'Text'), (b'html', b'HTML'), (b'md', b'Markdown')])),
                ('template', models.CharField(unique=True, max_length=255)),
                ('subject', models.CharField(max_length=255)),
                ('body', models.TextField()),
            ],
        ),
    ]
