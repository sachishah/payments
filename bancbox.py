__author__ = 'sshah'

import base64, os, logging, sys, httplib, datetime, suds
from suds import WebFault
from suds.wsse import Security, UsernameToken
from suds.client import Client as SudsClient
from payments.models import Payment
from profiles.models import UserProfile
from loans.models import Loan, LoanPartner
from datetime import timedelta, date
from django.contrib.auth.models import User

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)

url = 'http://stgws1.cftpay.com:8080/wsrv/npn.wsdl'
security = Security()
token = UsernameToken('', '')
security.tokens.append(token)

client = SudsClient(url)
client.set_options(wsse=security)

cache = client.options.cache
cache.setduration(days=10)

############ ENTIRE TRANSACTION #############

class BancboxBackend(object):
    s_id = 202017

    def __init__(self):
        pass

    def add_client(self, profile):
        user = User.objects.get(pk=profile.id)
        dob = profile.date_of_birth
        self.create_client(profile.id, user.first_name, user.last_name, profile.ssn, dob.strftime("%m/%d/%Y"),
                           profile.street, profile.city, profile.state, profile.zip, profile.phone, user.email)
        account_id = self.create_bank_account(profile.id, profile.routing_number, profile.account_type,
                                              profile.account_number, user.first_name)
        profile.bancbox_bankaccountid = account_id
        profile.save()

    def _schedule_payment(self, payment, payor, payee):
        draft = self.create_draft_schedule(payor.profile_id, (UserProfile.objects.get(pk=payor.profile_id)).bancbox_bankaccountid, payment.amount, payment.date)
        settlement_date = payment.date+timedelta(6)
        fee = self.create_fee_schedule(payor.profile_id, self.get_subscriber_fee_id(payor.profile_id), payment.fee, settlement_date)
        settlement = self.create_settlement_schedule(payee.profile_id, self.create_subscriber_payee(), payment.amount-payment.fee,
                                                     (UserProfile.objects.get(pk=payee.profile_id)).bancbox_bankaccountid, settlement_date)

    def schedule_payments(self, loan):
        payments = Payment.objects.filter(loan=loan.uuid)
        partners = LoanPartner.objects.filter(loan=loan.uuid)
        if partners.count()==2:
            payor = partners.get(role="lender")
            payee = partners.get(role="borrower")
            self.create_enrollment_document(payor.profile_id, payor.draft_agreement)
            self.create_enrollment_document(payee.profile_id, payee.draft_agreement)
            self._schedule_payment(payments.get(payment_type="disbursement"), payor, payee)
            repayment=payments.filter(payment_type="reimbursement")
            for payment in repayment:
                self._schedule_payment(payment, payee, payor)

    ############ CLIENT ############
    def create_client(self, id, f_name, l_name, social, dob, address, city, state, zip, phone, email):
        birthdate = client.factory.create("ns1:NpnDate")
        birthdate.date._value = dob
        birthdate.date._format = 'MM/dd/yyyy'

        client.service.CreateClient(externalClientId=id,
                                    subscriberId=self.s_id,
                                    firstname=f_name,
                                    lastname=l_name,
                                    ssn=social,
                                    dob=birthdate,
                                    address1=address,
                                    city=city,
                                    state=state,
                                    zip=zip,
                                    phone=phone,
                                    email=email,
                                    draftAmount=0)

    def create_enrollment_document(self, client_id, file, note=""):

        encoded_sva = base64.b64encode(open(file).read())

        document = client.service.CreateEnrollmentDocument(subscriberId=self.s_id,
                                                externalClientId=client_id,
                                                note=note,
                                                contentType='application/pdf',
                                                base64EncodedContent=encoded_sva,
                                                documentName=file)

        return document.documentId

    def update_client(self, client_id, f_name, l_name, ssn, dob, address, city, state, zip):
        client.service.UpdateClient(subscriberId=self.s_id,
                                    externalClientId=client_id,
                                    firstname=f_name,
                                    lastname=l_name,
                                    ssn=ssn,
                                    dob=dob,
                                    address1=address,
                                    city=city,
                                    state=state,
                                    zip=zip)

    def get_client(self, client_id):
        print client.service.GetClient(subscriberId=self.s_id,
                                       clientId=client_id)

    def get_clients(self, ascending, page_no, results_per_page):
        print client.service.GetClients(subscriberId=self.s_id,
                                        ascending=ascending,
                                        pageNo=page_no,
                                        resultsPerPage=results_per_page)

    def get_subscriber_fee_id(self, client_id):
        current_client = client.service.GetClient(subscriberId=self.s_id, externalClientId=client_id)
        return current_client.client.enrollment.enrollmentFees.fee[0].subscriberFeeId

    def verify_client(self, client_id):
        print client.service.ClientVerification(subscriberId=self.s_id,
                                                externalClientId=client_id)

    ############ BANK ACCOUNT ############

    def create_bank_account(self, client_id, routing_number, account_type, account_number, client_name):
        account = client.service.CreateClientBankAccount(subscriberId=self.s_id,
                                               externalClientId=client_id,
                                               routingNumber=routing_number,
                                               accountType=account_type,
                                               accountNumber=account_number,
                                               holdersName=client_name)
        return account.clientBankAccountId

    def update_bank_account(self, client_id, bank_account_id, routing_number, account_type, account_number, client_name):
        client.service.UpdateClientBankAccount(subscriberId=self.s_id,
                                               externalClientId=client_id,
                                               clientBankAccountId=bank_account_id,
                                               routingNumber=routing_number,
                                               accountType=account_type,
                                               accountNumber=account_number,
                                               holdersName=client_name)

    def get_bank_account(self, client_id, bank_account_id):
        return client.service.GetClientBankAccount(subscriberId=self.s_id,
                                            externalClientId=client_id,
                                            clientBankAccountId=bank_account_id)

    ############ DRAFT ############

    def create_draft_schedule(self, client_id, bank_account_id, amount, start_date):
        start = client.factory.create("ns1:NpnDate")
        start.date._value = start_date.strftime("%m/%d/%Y")
        start.date._format = 'MM/dd/yyyy'
        list = client.service.CreateDraftSchedule(subscriberId=self.s_id,
                                           externalClientId = client_id,
                                           clientBankAccountId=bank_account_id,
                                           amount=amount,
                                           occurs=1,
                                           startDate=start,
                                           type='ADHOC')
        return list.scheduleList.schedule[0].scheduleId

    def update_draft_schedule(self, schedule_id, bank_account_id, status, amount, date, type):
        client.service.UpdateDraftSchedule(scheduleId=schedule_id,
                                           subscriberId=self.s_id,
                                           clientBankAccountId=bank_account_id,
                                           sttus=status,
                                           amount=amount,
                                           scheduleDate=date,
                                           Type=type)

    def get_draft_schedule(self, schedule_id):
        print client.service.GetDraftScheduleList(subscriberId=self.s_id,
                                            scheduleId=schedule_id)

    def get_draft_schedule_list(self, start_date, end_date, order, ascending, status):
        print client.service.GetDraftScheduleList(subscriberId=self.s_id,
                                            startDate=start_date,
                                            endDate=end_date,
                                            order=order,
                                            ascending=ascending,
                                            status=status)

    def suspend_draft_schedule(self, client_id):
        client.service.SuspendDraftSchedule(subscriberId=self.s_id,
                                            externalClientId=client_id)

    ############ FEE ############

    def create_fee_schedule(self, client_id, subscriber_fee_id, amount, start_date):
        start = client.factory.create("ns1:NpnDate")
        start.date._value = start_date.strftime("%m/%d/%Y")
        start.date._format = 'MM/dd/yyyy'
        fee = client.service.CreateFeeSchedule(subscriberId=self.s_id,
                                           externalClientId = client_id,
                                           subscriberFeeId=subscriber_fee_id,
                                           amount=amount,
                                           occurs=1,
                                           startDate=start)
        return fee.scheduleId

    def update_fee_schedule(self, schedule_id, client_id, amount, date, update_remaining_schedules):
        client.service.UpdateFeeSchedule(subscriberId=self.s_id,
                                         scheduleId=schedule_id,
                                         externalClientId=client_id,
                                         amount=amount,
                                         scheduleDate=date,
                                         updateRemainingSchedule=update_remaining_schedules)

    def get_fee_schedule(self, client_id, scheduleId):
        print client.service.GetFeeSchedule(subscriberId=self.s_id,
                                            externalClientId=client_id,
                                            scheduleId=scheduleId)

    def get_fee_schedule_list(self, start_date, end_date, order, ascending, status):
        print client.service.GetFeeScheduleList(subscriberId=self.s_id,
                                          startDate=start_date,
                                          endDate=end_date,
                                          order=order,
                                          ascending=ascending,
                                          status=status)

    def suspend_fee_schedule(self, client_id=''):
        client.service.SuspendFeeSchedule(subscriberId=self.s_id,
                                          externalClientId=client_id)

    ############ TRANSACTION ############

    def get_transaction_list(self, client_id):
        print client.service.GetTransactionList(subscriberId=self.s_id,
                                          externalClientId=client_id)

    def get_transaction_details(self, transaction_id, schedule_id, include_check_image):
        print client.service.GetTransactionDetails(subscriberId=self.s_id,
                                                   transactionId=transaction_id,
                                                   scheduleId=schedule_id,
                                                   includeCheckImage=include_check_image)

    ############ ENROLLMENT ############

    def get_enrollment_exception_list(self, ascending, client_id=''):
        print client.service.GetEnrollmentExceptionList(subscriberId=self.s_id,
                                                  ascending=ascending,
                                                  externalClientId=client_id)

    ############ SUBSCRIBER PAYEE ############

    def create_subscriber_payee(self):
        payee = client.service.CreateSubscriberPayee(subscriberId=self.s_id,
                                             payeeName='LF')
        return payee.payeeId

    def update_subscriber_payee(self, payee_id, name):
        client.service.UpdateSubscriberPayee(subscriberId=self.s_id,
                                             payeeId=payee_id,
                                             payeeName=name)

    def get_subscriber_payee(self, payee_id):
        print client.service.GetSubscriberPayee(subscriberId=self.s_id,
                                          payeeId=payee_id)

    def get_subscriber_payee_list(self, page_number, number_per_page, ascending):
        print client.service.GetSubscriberPayee(subscriberId=self.s_id,
                                          pageNumber=page_number,
                                          numberOfRecordsPerPage=number_per_page,
                                          Ascending=ascending)

    def get_subscriber_payee_list_by_name(self):
        print client.service.GetSubscriberPayeeByName(subscriberId=self.s_id)

    ############ SETTLEMENT ############

    def create_settlement_schedule(self, client_id, payee_id, amount, account_number, start_date):
        start = client.factory.create("ns1:NpnDate")
        start.date._value = start_date.strftime("%m/%d/%Y")
        start.date._format = 'MM/dd/yyyy'
        schedule = client.factory.create("ns1:SettlementSchedule")
        schedule.effectiveDate = start
        schedule.paymentAmount = amount
        schedule.payeeId = payee_id
        schedule.transactionMethod = 'WIRE'
        list = client.factory.create('ns1:SettlementScheduleList')
        list.SettlementScheduleInfo.append(schedule)
        settlementList = client.service.CreateSettlementSchedule(subscriberId=self.s_id,
                                                externalClientId=client_id,
                                                payeeId=payee_id,
                                                currentBalance=0,
                                                settlementAmount=amount,
                                                numPayments = 1,
                                                accountNumber=account_number,
                                                isApprovalRequired=1,
                                                settlementScheduleList=list)
        return settlementList.scheduleId

    def get_client_settlement_list(self, from_date, to_date, page_number, number_per_page):
        start = client.factory.create('ns1:NpnDate')
        start.date._value = from_date
        start.date._format = 'MM/dd/yyyy'
        end = client.factory.create('ns1:NpnDate')
        end.date._value = to_date
        end.date._format = 'MM/dd/yyyy'
        print client.service.GetClientSettlementList(subscriberId=self.s_id,
                                               fromDate=start,
                                               toDate=end,
                                               pageNumber=page_number,
                                               numberOfRecordsPerPage=number_per_page)
'''
    ############ PAYMENT ############

    def update_payment(self, external_reference_id, update_payment_list, client_id, payee_id, payment_id, method):
        client.service.UpdatePaymentRequest(externalReferenceId=external_reference_id,
                                            updatePaymentList=update_payment_list)
        client.service.UpdatePayment(SubscriberId=self.s_id,
                                     externalClientId=client_id,
                                     PayeeId=payee_id,
                                     PaymentId=payment_id,
                                     transactionMethod=method)

    def get_payment_list(self, from_date, to_date, order_by, order, ascending, client_ids=''):
        print client.service.GetPaymentListRequest(subscriberId=self.s_id,
                                      fromDate=from_date,
                                      toDate=to_date,
                                      externalClientIds=client_ids)
        print client.service.PaymentOrder(orderBy=order_by)
        print client.service.PaymentOrderBy(order=order,
                                      isAscending=ascending)

    def get_payment_details(self, schedule_id):
        print client.service.GetPaymentDetails(subscriberId=self.s_id,
                                         scheduleId=schedule_id)


    ############ AFFILIATE ############

    def create_affiliate(self, name, address, city, state, zip, email, phone, businessType, taxId, bankName='', routingNumber='',
                        accountType='', accountNumber=''):
        client.service.CreateAffiliate(subscriberId=self.s_id,
                                       name=name,
                                       address1=address,
                                       city=city,
                                       state=state,
                                       zipcode=zip,
                                       email=email,
                                       phone=phone,
                                       businessType=businessType,
                                       taxId=taxId,
                                       bankName=bankName,
                                       routingNumber=routingNumber,
                                       accountType=accountType,
                                       accountNumber=accountNumber)

    def update_affiliate(self, affiliateId, name, address, city, state, zip, email, phone, businessType, taxId, bankName='',
                        routingNumber='', accountType='', accountNumber=''):
        client.service.UpdateAffiliate(subscriberId=self.s_id,
                                       affiliateId=affiliateId,
                                       name=name,
                                       address1=address,
                                       city=city,
                                       state=state,
                                       zipcode=zip,
                                       email=email,
                                       phone=phone,
                                       businessType=businessType,
                                       taxId=taxId,
                                       bankName=bankName,
                                       routingNumber=routingNumber,
                                       accountType=accountType,
                                       accountNumber=accountNumber)

    def get_affiliate(self, affiliateId=''):
        print client.service.getAffiliate(subscriberId=self.s_id,
                                    affiliateId=affiliateId)

    def get_affiliate_list(self, pageNumber, resultsPerPage):
        print client.service.GetAffiliateList(subscriberId=self.s_id,
                                        pageNo=pageNumber,
                                        resultsPerPage=resultsPerPage)

    def update_affiliate_document_request(self, affiliateId, externalAffiliateId, documentId, note, name, contentType):
        client.service.UpdateAffiliateDocumentRequest(subscriberId=self.s_id,
                                                      affiliateId=affiliateId,
                                                      externalAffiliateId=externalAffiliateId,
                                                      documentId=documentId,
                                                      note=note,
                                                      name=name,
                                                      contentType=contentType)

    ############ RULE SET ###########

    def create_rule_set_request(self, name, externalRuleSetId):
        client.service.CreateRuleSetRequest(subscriberId=self.s_id,
                                            name=name,
                                            externalRuleSetId=externalRuleSetId)

    def update_rule_set_request(self, ruleSetId='', name='', status=''):
        client.service.UpdateRuleSetRequest(subscriberId=self.s_id,
                                            ruleSetId=ruleSetId,
                                            name=name,
                                            status=status)

    def get_rule_set_request(self, ruleSetId=''):
        print client.service.GetRuleSetRequest(subscriberId=self.s_id,
                                         ruleSetId=ruleSetId)



def SchedulePayments(fName, lName, social, dob, address, city, state, zip, phone, amount, email, docName, contentType, docType,
          routingNumber, accType, accNumber, draftAmount, draftOccurs, draftStartDate, draftType, feeAmount, feeOccurs,
          feeStartDate, fName2, lName2, social2, dob2, address3, city2, state2, zip2, phone2, amount2, email2, docName2,
          contentType2, docType2, routingNumber2, accType2, accNumber2, settlementAmount, settlementOccurs, settlementStartDate,

          mName='', address2='', workNumber='', mobile='', note='', mName2='', address4='', workNumber2='', mobile2='', note2=''):

    #creating 2 clients
    clientId1 = createClient(fName, lName, social, dob, address, city, state, zip, phone, amount, email, mName,
                             address2, workNumber, mobile)
    clientId2 = createClient(fName2, lName2, social2, dob2, address3, city2, state2, zip2, phone2, amount2, email2,
                             mName2, address4, workNumber2, mobile2)

    #creating their SVA documents
    documentId1 = createEnrollmentDocument(clientId1, note, docName, contentType, docType)
    documentId2 = createEnrollmentDocument(clientId2, note2, docName2, contentType2, docType2)

    #creating their bank accounts
    bankAccountId1 = createBankAccount(clientId1, routingNumber, accType, accNumber, fName)
    bankAccountId2 = createBankAccount(clientId2, routingNumber2, accType2, accNumber2, fName2)

    #setting the second client as the payee
    payeeId = createSubscriberPayee(fName+" "+lName, 1, accNumber2)

    #creating draft schedule
    draftId = createDraftSchedule(clientId1, bankAccountId1, draftAmount, draftOccurs, draftStartDate, draftType)

    #creating fee schedule
    feeId = createFeeSchedule(clientId1, getSubscriberFeeId(clientId1), feeAmount, feeOccurs, feeStartDate)

    #creating settlement schedule
    settlementId = createSettlementSchedule(clientId2, payeeId, amount2, settlementAmount, settlementOccurs, accNumber2,
                                            0, settlementStartDate)
    '''