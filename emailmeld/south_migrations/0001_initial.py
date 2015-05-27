# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'EmailMeldModel'
        db.create_table('emailmeld_emailmeldmodel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email_type', self.gf('django.db.models.fields.CharField')(default='MARKDOWN', max_length=10)),
            ('template', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('body', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('emailmeld', ['EmailMeldModel'])


    def backwards(self, orm):
        # Deleting model 'EmailMeldModel'
        db.delete_table('emailmeld_emailmeldmodel')


    models = {
        'emailmeld.emailmeldmodel': {
            'Meta': {'object_name': 'EmailMeldModel'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'email_type': ('django.db.models.fields.CharField', [], {'default': "'MARKDOWN'", 'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['emailmeld']