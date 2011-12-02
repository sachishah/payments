__author__ = 'sshah'

from django.db import models
from common.models import BaseModel
from profiles.models import UserProfile
from datetime import datetime
from loans.models import Loan

#################
## Payment
#################

PAYMENT_TYPES = (
    ('disbursement', 'disbursement'),
    ('repayment', 'repayment'),
)

class Payment(BaseModel):
    loan = models.ForeignKey(Loan) #ManyToOne
    payment_type = models.TextField(blank=False,null=False,choices=PAYMENT_TYPES)
    amount = models.DecimalField(blank=False,null=False,decimal_places=2,max_digits=20)
    fee = models.DecimalField(blank=False,null=False,decimal_places=2,max_digits=20)
    date = models.DateField(blank=False,null=False,default=datetime.now())