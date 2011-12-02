# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Payment'
        db.create_table('payments_payment', (
            ('uuid', self.gf('common.fields.UUIDField')(auto=True, unique=True, max_length=36, primary_key=True, db_index=True)),
            ('loan', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['loans.Loan'])),
            ('payment_type', self.gf('django.db.models.fields.TextField')()),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=2)),
            ('fee', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=2)),
            ('date', self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2011, 9, 1, 11, 45, 53, 290735))),
        ))
        db.send_create_signal('payments', ['Payment'])


    def backwards(self, orm):
        
        # Deleting model 'Payment'
        db.delete_table('payments_payment')


    models = {
        'loans.loan': {
            'Meta': {'object_name': 'Loan'},
            'uuid': ('common.fields.UUIDField', [], {'auto': 'True', 'unique': 'True', 'max_length': '36', 'primary_key': 'True', 'db_index': 'True'})
        },
        'payments.payment': {
            'Meta': {'object_name': 'Payment'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2011, 9, 1, 11, 45, 53, 290735)'}),
            'fee': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'loan': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['loans.Loan']"}),
            'payment_type': ('django.db.models.fields.TextField', [], {}),
            'uuid': ('common.fields.UUIDField', [], {'auto': 'True', 'unique': 'True', 'max_length': '36', 'primary_key': 'True', 'db_index': 'True'})
        }
    }

    complete_apps = ['payments']
