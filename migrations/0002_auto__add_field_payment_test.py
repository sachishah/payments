# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Payment.test'
        db.add_column('payments_payment', 'test', self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2011, 9, 1, 17, 31, 54, 621489)), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Payment.test'
        db.delete_column('payments_payment', 'test')


    models = {
        'loans.loan': {
            'Meta': {'object_name': 'Loan'},
            'uuid': ('common.fields.UUIDField', [], {'auto': 'True', 'unique': 'True', 'max_length': '36', 'primary_key': 'True', 'db_index': 'True'})
        },
        'payments.payment': {
            'Meta': {'object_name': 'Payment'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2011, 9, 1, 17, 31, 54, 621457)'}),
            'fee': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'loan': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['loans.Loan']"}),
            'payment_type': ('django.db.models.fields.TextField', [], {}),
            'test': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2011, 9, 1, 17, 31, 54, 621489)'}),
            'uuid': ('common.fields.UUIDField', [], {'auto': 'True', 'unique': 'True', 'max_length': '36', 'primary_key': 'True', 'db_index': 'True'})
        }
    }

    complete_apps = ['payments']
