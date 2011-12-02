__author__ = 'sshah'

import unittest
from loans.models import Loan, LoanPartner
from profiles.models import UserProfile
from payments.models import Payment
from django.contrib.auth.models import User
from django.test import TestCase
from bancbox import BancboxBackend

class MyTestCase(TestCase):
    fixtures = [
       "profiles/fixtures/profiles.json",
       "loans/fixtures/loans.json",
       "payments/fixtures/payments.json",
    ]

    def my_test(self):
        BancboxBackend.add_client(BancboxBackend(), UserProfile.objects.get(pk=1))
        BancboxBackend.add_client(BancboxBackend(), UserProfile.objects.get(pk=2))
        BancboxBackend.schedule_payments(BancboxBackend(), Loan.objects.get(pk="6633a0c6-6ac3-47b8-b4f7-756d2a66c3b9"))
'''
from decimal import Decimal
from django.db.models import Sum
from django.test import TestCase
from django.core.urlresolvers import reverse

from advertising.constants import AD_TRACKING_QUERY_STRING_KEY
from advertising.models import AdVariation, FacebookAd
from analytics.models import Visit, PerformanceEvent, PageView,PerformanceEventType, UserIdentifier
from analytics.constants import *

from client_management.models import Client

import base64

class TestTrackingAdAttribution(TestCase):
   fixtures = [
       "fixtures/payments.json",
       "profiles/fixtures/profiles.json",
   ]

   def test_cookie_based_attribution(self):
       facebook_ad = FacebookAd.objects.get(pk="6b7aa9b8-577a-484a-b8aa-3f794a69e68b")
       ad_variation = facebook_ad.variation

       #first lets make a request to the site that sets the ADID and hopefully sets the cookie
       response = self.client.get(reverse("test_page")+"?%s=%s" % (AD_TRACKING_QUERY_STRING_KEY,facebook_ad.pk))

       tracking_querystring = "?%s=%s" % (USER_IDENTIFIER_KEY,"9876")
       tracking_response = self.client.get(reverse('ajax_track_performance_event') + tracking_querystring)

       self.assertEqual(PerformanceEvent.objects.get_for_ad_variation(ad_variation).count(), 1)

   def test_cookie_middleware(self):

       #test no cookie
       response = self.client.get(reverse("test_page"))

       self.assertEqual(
           str(response.cookies),
           ""
       )

       #test the first ADID gets stored
       response2 = self.client.get(reverse("test_page")+"?adid=6b7aa9b8-577a-484a-b8aa-3f794a69e68b")
       self.assertEqual(
           len(response2.cookies.keys()),
           1
       )
       self.assertEqual(
           response2.cookies.keys()[0],
           '__ASIDS'
       )

       cookie_value = response2.cookies.values()[0].value
       self.assertEqual(
           base64.b64decode(cookie_value),
           '{"861ee53c-5c75-41e3-ab37-1a68d3848dc7": {"1": null, "0": "6b7aa9b8-577a-484a-b8aa-3f794a69e68b"}}'
       )


       #test the second cookie gets stored as the LAST
       response3 = self.client.get(reverse("test_page")+"?adid=6b7aa9b8-577a-484a-b8aa-3f794a69e68b")
       cookie_value2 = response3.cookies.values()[0].value
       self.assertEqual(
           base64.b64decode(cookie_value2),
           '{"861ee53c-5c75-41e3-ab37-1a68d3848dc7": {"1": "6b7aa9b8-577a-484a-b8aa-3f794a69e68b", "0": "6b7aa9b8-577a-484a-b8aa-3f794a69e68b"}}'
       )


#
#        #test the second cookie gets stored as the LAST
#        response3 = self.client.get(reverse("test_page")+"?adid=adstack")
#        cookie_value2 = response3.cookies.values()[0].value
#        self.assertEqual(
#            base64.b64decode(cookie_value2),
#            '{"861ee53c-5c75-41e3-ab37-1a68d3848dc7": {"1": "adstack", "0": "6b7aa9b8-577a-484a-b8aa-3f794a69e68b"}}'
#        )
#
#
#        #test the third adid cookie gets stored as the LAST
#        response4 = self.client.get(reverse("test_page")+"?adid=evan")
#        cookie_value3 = response4.cookies.values()[0].value
#        self.assertEqual(
#            base64.b64decode(cookie_value3),
#            '{"861ee53c-5c75-41e3-ab37-1a68d3848dc7": {"1": "evan", "0": "6b7aa9b8-577a-484a-b8aa-3f794a69e68b"}}'
#        )


   def test_cookie_assignment(self):
       from analytics.middleware import ClientCookie, TrackingCookie
       test_client = Client.objects.get(name="AdStackTest")
       test_client_api_access_key = unicode(test_client.api_access_key)

       #first test that not passing in any data can still create a blank ClientCookie
       test_client_cookie = ClientCookie(test_client_api_access_key,data_dict={})
       self.assertEqual(
          test_client_cookie.to_key_value(),
           (test_client_api_access_key, {'1': None, '0': None})
       )

       #Now test that passing in the first cookie value creates the correct representation
       test_client_cookie = ClientCookie(test_client_api_access_key,data_dict={"0":"test"})
       self.assertEqual(
         test_client_cookie.to_key_value(),
          (test_client_api_access_key, {'1': None, '0': 'test'})
       )
       #Make sure the most recent key here is "test"
       self.assertEqual(test_client_cookie.get_most_recent(),'test')

       test_client_cookie = ClientCookie(test_client_api_access_key,data_dict={"0":"test","1":"last"})
       self.assertEqual(
           test_client_cookie.to_key_value(),
           (test_client_api_access_key, {'1': 'last', '0': 'test'})
       )
       #Make sure the most recent key here is "test"
       self.assertEqual(test_client_cookie.get_most_recent(),'last')


       #Test to see if the TrackingCookie can ouput correctly for 1 client, with one cookie
       cc0 = ClientCookie(test_client_api_access_key,data_dict={"0":"first1"})
       t0 = TrackingCookie()
       t0.client_cookies.append(cc0)
       self.assertEqual(
           t0.to_cookie_string(),
           'eyI4NjFlZTUzYy01Yzc1LTQxZTMtYWIzNy0xYTY4ZDM4NDhkYzciOiB7IjEiOiBudWxsLCAiMCI6ICJmaXJzdDEifX0='
       )
       self.assertEqual(
           t0.get_most_recent_ad_variation_pk_for_client(test_client),
           "first1"
       )


       #Test to see if the TrackingCookie can ouput correctly for 1 client
       cc1 = ClientCookie(test_client_api_access_key,data_dict={"0":"first1","1":"last1"})
       t = TrackingCookie()
       t.client_cookies.append(cc1)
       self.assertEqual(
           t.to_cookie_string(),
           'eyI4NjFlZTUzYy01Yzc1LTQxZTMtYWIzNy0xYTY4ZDM4NDhkYzciOiB7IjEiOiAibGFzdDEiLCAiMCI6ICJmaXJzdDEifX0='
       )
       self.assertEqual(
           t.get_most_recent_ad_variation_pk_for_client(test_client),
           "last1"
       )


       #Test to see if the TrackingCookie can ouput correctly for 2 clients
       # Should be: '{"client1": {"1": "last1", "0": "first1"}, "client2": {"1": "last2", "0": "first2"}}'
       cc2 = ClientCookie("client2",data_dict={"0":"first2","1":"last2"})
       t.client_cookies.append(cc2)
       self.assertEqual(
           t.to_cookie_string(),
           'eyJjbGllbnQyIjogeyIxIjogImxhc3QyIiwgIjAiOiAiZmlyc3QyIn0sICI4NjFlZTUzYy01Yzc1LTQxZTMtYWIzNy0xYTY4ZDM4NDhkYzciOiB7IjEiOiAibGFzdDEiLCAiMCI6ICJmaXJzdDEifX0='
       )


       #try to add back the same one and make sure it hasnt changed
       t.client_cookies.append(cc1)
       self.assertEqual(
           t.to_cookie_string(),
           'eyJjbGllbnQyIjogeyIxIjogImxhc3QyIiwgIjAiOiAiZmlyc3QyIn0sICI4NjFlZTUzYy01Yzc1LTQxZTMtYWIzNy0xYTY4ZDM4NDhkYzciOiB7IjEiOiAibGFzdDEiLCAiMCI6ICJmaXJzdDEifX0='
       )

       #now try to create one of these objects from a string

       #cookie_string = '{"client1": {"1": "last1", "0": "first1"}, "client2": {"1": "last2", "0": "first2"}}'
       self.assertEqual(
           base64.b64encode('{"client1": {"1": "last1", "0": "first1"}, "client2": {"1": "last2", "0": "first2"}}'),
           'eyJjbGllbnQxIjogeyIxIjogImxhc3QxIiwgIjAiOiAiZmlyc3QxIn0sICJjbGllbnQyIjogeyIxIjogImxhc3QyIiwgIjAiOiAiZmlyc3QyIn19'
       )

       #Test Normal Cookie Decoding
       cookie_string = 'eyJjbGllbnQxIjogeyIxIjogImxhc3QxIiwgIjAiOiAiZmlyc3QxIn0sICJjbGllbnQyIjogeyIxIjogImxhc3QyIiwgIjAiOiAiZmlyc3QyIn19'
       t2 = TrackingCookie(cookie_string)
       self.assertEqual(
           t2.to_cookie_string(),
           cookie_string
       )

       #Test Bad JSON encoding
       #Check what happens when something decodes correctly, but then can't be parsed by simplejson
       cookie_string = 'bad_json='
       t3 = TrackingCookie(cookie_string)
       self.assertEqual(
           t3.to_cookie_string(),
           base64.b64encode("{}")
       )

       #Test BAD cookie encoding
       #when there is bad encoding the behaviour should be to not load the bad data
       cookie_string = "bad_encoding"
       t4 = TrackingCookie(cookie_string)
       self.assertEqual(
           t4.to_cookie_string(),
           base64.b64encode("{}")
       )

       #Test fucked up cookies
       cookie_string = 'm\xa7c\xb2\x89'
       t5 = TrackingCookie(cookie_string)
       self.assertEqual(
           t5.to_cookie_string(),
           base64.b64encode("{}")
       )



class TestAnalyticsTracking(TestCase):
   fixtures = [
       "fixtures/payments.json",
       "profiles/fixtures/profiles.json",
   ]

   conversion_kwargs = {
       AD_TRACKING_QUERY_STRING_KEY : "6b7aa9b8-577a-484a-b8aa-3f794a69e68b",
       "testing":"true"
   }

   conversion_meta = {
       "HTTP_REFERER" : "http://www.adstack.com/fake/referer/",
       "HTTP_USER_AGENT": "unit-test-client"
   }

   def build_query_string(self, query_string_dictionary):
       return "?%s" % "&".join(["%s=%s" % (k,v) for k,v in query_string_dictionary.items()])


   def _verify_pe_counts(self, test_client, view_kwargs, total_count, total_value):
       response = self.client.get(reverse("track_performance_event_image_with_parameters", kwargs=view_kwargs))
       self.assertEquals(
           PerformanceEvent.objects.filter(client=test_client,type=PerformanceEventType.objects.get_default(test_client)).count(),
           total_count
       )
       self.assertEqual(
           PerformanceEvent.objects.filter(client=test_client,type=PerformanceEventType.objects.get_default(test_client)).aggregate(Sum("value"))["value__sum"],
           total_value
       )

   def test_parameter_tracking_view(self):
       test_client = Client.objects.get(name="AdStackTest")

       #1) test what happens when we call this view with only the api_key and the event type
       view_kwargs = dict(
           api_key=test_client.api_access_key,
           event_type_name = DEFAULT_PERFORMANCE_EVENT_TYPE_NAME
       )
       self._verify_pe_counts(test_client, view_kwargs, 1, Decimal("1.00"))

       #2) test what happens when we also call the performance tracking with:
       view_kwargs.update(dict(event_value="2.50"))
       self._verify_pe_counts(test_client, view_kwargs, 2, Decimal("3.50"))

       #3) test what happens when we also call the performance tracking with:
       view_kwargs.update(dict(unique_id="1234"))
       self._verify_pe_counts(test_client, view_kwargs, 3, Decimal("6.00"))

       self.assertEqual(
           PerformanceEvent.objects.get_for_user_id("1234").count(),
           1
       )
       self.assertEqual(
           PerformanceEvent.objects.get_for_user_id("1234").aggregate(Sum("value"))["value__sum"],
           Decimal("2.50")
       )

       #4) checking for messed up formatting of  Decimals
       view_kwargs.update(dict(event_value="1..00"))
       self._verify_pe_counts(test_client, view_kwargs, 4, Decimal("7.00"))


   def _verify_pe_response(self, conversion_kwargs,
                           number_total_event_types=None,
                           event_type_name=None,
                           total_events=None,
                           total_value=None,
                           unique_identifier=None,
                           tracking_view_name ='ajax_track_performance_event'
   ):
       response = self.client.get(reverse(tracking_view_name) + self.build_query_string(conversion_kwargs), **self.conversion_meta)
       extra_kwargs = {}
       if unique_identifier:
           extra_kwargs.update(dict(user_identifier__unique_identifier=unique_identifier))

       self.assertEqual(response.status_code, 200)

       if tracking_view_name != "track_performance_event_image":
           self.assertContains(response, PerformanceEvent.objects.latest("date_created").pk.hex, 1)
       if number_total_event_types:
           self.assertEqual(PerformanceEventType.objects.count(), number_total_event_types)
       if event_type_name:
           self.assertEqual(PerformanceEventType.objects.filter(name=event_type_name).count(), 1)
           if total_events:
               self.assertEqual(PerformanceEvent.objects.filter(**extra_kwargs).filter(type__name=event_type_name).count(), total_events)
           if total_value:
               self.assertEqual(PerformanceEvent.objects.filter(**extra_kwargs).filter(type__name=event_type_name).aggregate(Sum("value"))["value__sum"],total_value)

   def test_performance_tracking(self):
       conversion_kwargs = self.conversion_kwargs

       self._verify_pe_response(conversion_kwargs, number_total_event_types=1, event_type_name=DEFAULT_PERFORMANCE_EVENT_TYPE_NAME, total_events=1, total_value=Decimal("1.00"))
       self.assertEqual(PerformanceEvent.objects.get_conversions().count(),1)

       conversion_kwargs.update({
           USER_IDENTIFIER_KEY: "1234",
           PERFORMANCE_EVENT_TYPE_KEY: DEFAULT_PERFORMANCE_EVENT_TYPE_NAME
       })
       self._verify_pe_response(conversion_kwargs, number_total_event_types=1, event_type_name=DEFAULT_PERFORMANCE_EVENT_TYPE_NAME, total_events=2, total_value=Decimal("2.00"))
       self.assertEqual(PerformanceEvent.objects.get_conversions().count(),2)

       conversion_kwargs.pop(AD_TRACKING_QUERY_STRING_KEY)
       conversion_kwargs.update({PERFORMANCE_EVENT_TYPE_KEY: "EmailClick"})

       self._verify_pe_response(conversion_kwargs, number_total_event_types=2, event_type_name="EmailClick", total_events=1, total_value=Decimal("1.00"))

       conversion_kwargs.update({PERFORMANCE_EVENT_VALUE_KEY: "1"})
       self._verify_pe_response(conversion_kwargs, number_total_event_types=2, event_type_name="EmailClick", total_events=2, total_value=Decimal("2.00"))

       conversion_kwargs.update({PERFORMANCE_EVENT_VALUE_KEY: "2"})
       self._verify_pe_response(conversion_kwargs, number_total_event_types=2, event_type_name="EmailClick", total_events=3, total_value=Decimal("4.00"), tracking_view_name="track_performance_event_image")

       conversion_kwargs.update({PERFORMANCE_EVENT_VALUE_KEY: "2.50"})
       self._verify_pe_response(conversion_kwargs, number_total_event_types=2, event_type_name="EmailClick", total_events=4, total_value=Decimal("6.50"), tracking_view_name="track_performance_event_image")

       conversion_kwargs.update({
           PERFORMANCE_EVENT_TYPE_KEY: "Checkout",
           PERFORMANCE_EVENT_VALUE_KEY: "10.00"
       })
       self._verify_pe_response(conversion_kwargs, event_type_name="Checkout", total_events=1, total_value=Decimal("10.00"), unique_identifier="1234")

       conversion_kwargs.update({PERFORMANCE_EVENT_VALUE_KEY: "12.50"})
       self._verify_pe_response(conversion_kwargs, event_type_name="Checkout", total_events=2, total_value=Decimal("22.50"), unique_identifier="1234")


       ad_variation = AdVariation.objects.get(facebook_ad__pk="6b7aa9b8-577a-484a-b8aa-3f794a69e68b")
       self.assertEqual(PerformanceEvent.objects.get_for_ad_variation(ad_variation).filter(type__name="Conversion").count(), 1)
       self.assertEqual(PerformanceEvent.objects.get_for_ad_variation(ad_variation).filter(type__name="EmailClick").count(), 4)
       self.assertEqual(PerformanceEvent.objects.get_for_ad_variation(ad_variation).filter(type__name="Checkout").count(), 2)



       conversion_kwargs.update({
           USER_IDENTIFIER_KEY: "9876",
           PERFORMANCE_EVENT_TYPE_KEY: "Checkout",
           PERFORMANCE_EVENT_VALUE_KEY: "10.00"
       })
       self._verify_pe_response(conversion_kwargs, event_type_name="Checkout", total_events=1, total_value=Decimal("10.00"), unique_identifier="9876")

       conversion_kwargs.update({
           USER_IDENTIFIER_KEY: "9876",
           PERFORMANCE_EVENT_TYPE_KEY: "Checkout",
           PERFORMANCE_EVENT_VALUE_KEY: "10..00"
       })
       self._verify_pe_response(conversion_kwargs, event_type_name="Checkout", total_events=2, total_value=Decimal("20.00"), unique_identifier="9876")

       #here we're going to test that when a new user comes in we store the utm tags for the first time we correctly
       # create these from the
#        conversion_kwargs.update({
#            USER_IDENTIFIER_KEY: "AS_TEST_USER",
#            "utm_source" : "TestSource",
#            "utm_medium" : "TestMedium",
#            "utm_content" : "TestContent",
#            "utm_campaign" : "TestCampaign"
#        })
#        response = self.client.get(reverse('ajax_track_performance_event') + self.build_query_string(conversion_kwargs), **self.conversion_meta)
#        ui = UserIdentifier.objects.get(unique_identifier="AS_TEST_USER")
#        self.assertEqual(ui.source.name, "TestSource")
#        self.assertEqual(ui.campaign.name, "TestCampaign")
#        self.assertEqual(ui.content.name, "TestContent")
#        self.assertEqual(ui.medium.name, "TestMedium")



   def test_default_tracking(self):

       query_string = "?%s" % "&".join(["%s=%s" % (k,v) for k,v in self.conversion_kwargs.items()])

       response = self.client.get(reverse('ajax_track_page_view'), **self.conversion_meta)
       self.assertContains(response, "NO ADID", 1, 200)

       response = self.client.get(reverse('ajax_track_conversion'), **self.conversion_meta)
       self.assertContains(response, "NO ADID", 1, 200)

       self.assertEqual(PageView.objects.count(), 0)
       self.assertEqual(PerformanceEvent.objects.count(), 0)
       self.assertEqual(Visit.objects.count(), 0)

       response = self.client.get(reverse('ajax_track_page_view') + query_string, **self.conversion_meta)
       self.assertContains(response, PageView.objects.latest("date_created").pk.hex, 1)


       self.assertEqual(PageView.objects.count(), 1)
       self.assertEqual(PerformanceEvent.objects.count(), 0)
       self.assertEqual(Visit.objects.count(), 1)

       response = self.client.get(reverse('ajax_track_page_view') + query_string, **self.conversion_meta)
       self.assertContains(response, PageView.objects.latest("date_created").pk.hex, 1)

       self.assertEqual(PageView.objects.count(), 2)
       self.assertEqual(PerformanceEvent.objects.count(), 0)
       self.assertEqual(Visit.objects.count(), 1)

       response = self.client.get(reverse('ajax_track_conversion') + query_string, **self.conversion_meta)
       self.assertContains(response, PerformanceEvent.objects.latest("date_created").pk.hex, 1)

       self.assertEqual(PerformanceEventType.objects.filter(name=DEFAULT_PERFORMANCE_EVENT_TYPE_NAME).count(), 1)
       self.assertEqual(PerformanceEvent.objects.filter(type__name=DEFAULT_PERFORMANCE_EVENT_TYPE_NAME).count(), 1)

       self.assertEqual(PageView.objects.count(), 2)
       self.assertEqual(PerformanceEvent.objects.count(), 1)
       self.assertEqual(Visit.objects.count(), 1)

       self.assertDictEqual(
           PerformanceEvent.objects.get().get_signed_data_for_wire(),
           {'type': 'Conversion', 'data': u'FZbKdqvCp45RPtqKvc7qnd67aO+fkK6nv4TtN7NaZ0I=.eyJnZXRfcGFyYW1ldGVycyI6IHsidGVzdGluZyI6ICJ0cnVlIiwgImFkaWQiOiAiNmI3YWE5YjgtNTc3YS00ODRhLWI4YWEtM2Y3OTRhNjllNjhiIn19'}
       )

import unittest
from django.test import TestCase
from validation import ValidationFormulas

#Here are some bank numbers that we can run tests against...
SHORT_BAD_ABN_NUM = 1000012
LONG_BAD_ABN_NUM = 255073345999
BAD_ABN_NUM = 255073545
GOOD_ABN_NUM = 255073345

class ValidatorsTestCase(unittest.TestCase):

    def setUp(self):
        self.value = CITY_CODE_FRAUD

    def testAbnAlgorythm(self):
        """Tests the algorythm with a known good bank number.
           This test is here to create the algorythm to be used
             in the validator implementation.  When it's right,
             cut and paste it into the validator class.

           The algorithm checks the first second and third number
            and adds them together, then iterates through every
            three numbers (total of 9) to return a value.

           If the resulting sum is an even multiple of ten
            (but not zero), the ABA routing number is good.
           """
        n=0
        bank_str = str(GOOD_ABN_NUM)
        num_length = len(bank_str)
        if num_length==9:
            for j in range(0,num_length,3):
                t = int(bank_str[j]) #this is the first digit
                ti = int(bank_str[j + 1]) #this is the second digit
                tii = int(bank_str[j + 2]) #this is the third digit
                n += (t * 3)+ (ti * 7)+ tii #add them up
            #check for zero and modulus of 10
            print((n != 0) & ((n % 10) == 0))  #we'll take this line out when we get it right.
            self.assertTrue((n != 0) & ((n % 10) == 0))

    def testBankRouter(self):
        """Tests the algorythm in the validator against
              known good and bad bank numbers.
           """
        bank_num = self.SHORT_BAD_ABN_NUM
        formt = ValidationFormulas()
        bool = formt.isBankRoutingNumber(bank_num)
        self.assertFalse(bool)

        bank_num = self.LONG_BAD_ABN_NUM
        formt = ValidationFormulas()
        bool = formt.isBankRoutingNumber(bank_num)
        self.assertFalse(bool)

        bank_num = self.BAD_ABN_NUM
        formt = ValidationFormulas()
        bool = formt.isBankRoutingNumber(bank_num)
        self.assertFalse(bool)

        bank_num = self.GOOD_ABN_NUM
        formt = ValidationFormulas()
        bool = formt.isBankRoutingNumber(bank_num)
        self.assertTrue(bool)
'''