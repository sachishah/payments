__author__ = 'sshah'

# -*- coding: utf-8 -*-

#######################################################################################
# Python implementation of RightSignature OAuth                                       #
#                                                                                     #
# Original LinkedIn API Library by Ozgur Vatansever <ozgurvt@gmail.com>               #
# RightSignature Modification by Cary Dunn <cary.dunn@gmail.com>                      #
#######################################################################################

"""
Provides a Pure Python RightSignature API Interface.
"""
import hashlib
sha = hashlib.sha1


import urllib, urllib2, time, random, httplib, hmac, binascii, cgi, string, datetime
from HTMLParser import HTMLParser

from xml.dom import minidom
from urlparse import urlparse
from xml.sax.saxutils import unescape

class OAuthError(Exception):
    """
    General OAuth exception, nothing special.
    """
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)


class Stripper(HTMLParser):
    """
    Stripper class that strips HTML entity.
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def getAlteredData(self):
        return ''.join(self.fed)


class XMLBuilder(object):
    def __init__(self, rootTagName):
        self.document = minidom.Document()
        self.root = self.document.createElement(rootTagName)
        self.document.appendChild(self.root)

    def xml(self):
        return self.document.toxml()

    def __unicode__(self):
        return self.document.toprettyxml()

    def append_element_to_root(self, element):
        self.root.appendChild(element)

    def append_list_of_elements_to_element(self, element, elements):
        map(lambda x:element.appendChild(x),elements)
        return element

    def create_element(self, tag_name):
        return self.document.createElement(str(tag_name))

    def create_element_with_text_node(self, tag_name, text_node):
        text_node = self.document.createTextNode(str(text_node))
        element = self.document.createElement(str(tag_name))
        element.appendChild(text_node)
        return element

    def create_elements(self, **elements):
        return [self.create_element_with_text_node(tag_name, text_node) for tag_name, text_node in elements.items()]


class RightSignature(object):
    def __init__(self, callback_url):
        """
        @ RightSignature OAuth Authorization
        ------------------------------
        In OAuth terminology, there are 2 tokens that we need in order to have permission to perform an API request.
        Those are requestToken and accessToken. Thus, this class basicly intends to wrap methods of OAuth spec. which
        are related of gettting requestToken and accessToken strings.

        @ Important Note:
        -----------------
        HMAC-SHA1 hashing algorithm will be used while encrypting a request body of an HTTP request. Other alternatives
        such as 'SHA-1' or 'PLAINTEXT' are ignored.

        @Reference for OAuth
        --------------------
        Please take a look at the link below if you have a basic knowledge of HTTP protocol
        - http://developer.linkedin.com/docs/DOC-1008


        Please create an application from the link below if you do not have an API key and secret key yet.
        - https://www.linkedin.com/secure/developer
        @api_key:    Your API key
        @api_secret: Your API secret key
        @callback_url: the return url when the user grants permission to Consumer.
        """
        # Credientials
        self.URI_SCHEME        = "https"
        self.API_ENDPOINT      = "rightsignature.com"
        self.REQUEST_TOKEN_URL = "/oauth/request_token"
        self.ACCESS_TOKEN_URL  = "/oauth/access_token"
        self.REDIRECT_URL      = "/oauth/authorize"
        self.version           = "1.0"
        self.signature_method  = "HMAC-SHA1" # as I said
        self.BASE_URL          = "%s://%s" % (self.URI_SCHEME, self.API_ENDPOINT)

        self.API_KEY       = ""
        self.API_SECRET    = ""
        self.CALLBACK_URL  = callback_url
        self.request_token = None # that comes later
        self.access_token  = None # that comes later and later

        self.request_token_secret = None
        self.access_token_secret  = None

        self.verifier = None
        self.error    = None

        self.request_oauth_nonce     = None
        self.request_oauth_timestamp = None
        self.access_oauth_nonce      = None
        self.access_oauth_timestamp  = None
        self.request_oauth_error     = None
        self.access_oauth_error      = None


    def getRequestTokenURL(self):
        return "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, self.REQUEST_TOKEN_URL)

    def getAccessTokenURL(self):
        return "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, self.ACCESS_TOKEN_URL)

    def getAuthorizeURL(self, request_token = None):
        self.request_token = request_token and request_token or self.request_token
        if self.request_token is None:
            raise OAuthError("OAuth Request Token is NULL. Plase acquire this first.")
        return "%s%s?oauth_token=%s" % (self.BASE_URL, self.REDIRECT_URL, self.request_token)

    #################################################
    # HELPER FUNCTIONS                              #
    # You do not explicitly use those methods below #
    #################################################
    def _generate_nonce(self, length = 20):
        return ''.join([string.letters[random.randint(0, len(string.letters) - 1)] for i in range(length)])

    def _generate_timestamp(self):
        return int(time.time())

    def _quote(self, st):
        return urllib.quote(st, safe='~')

    def _utf8(self, st):
        return isinstance(st, unicode) and st.encode("utf-8") or str(st)

    def _urlencode(self, query_dict):
        keys_and_values = [(self._quote(self._utf8(k)), self._quote(self._utf8(v))) for k,v in query_dict.items()]
        keys_and_values.sort()
        return '&'.join(['%s=%s' % (k, v) for k, v in keys_and_values])

    def _get_value_from_raw_qs(self, key, qs):
        raw_qs = cgi.parse_qs(qs, keep_blank_values = False)
        rs = raw_qs.get(key)
        if type(rs) == list:
            return rs[0]
        else:
            return rs

    def _signature_base_string(self, method, uri, query_dict):
        return "&".join([self._quote(method), self._quote(uri), self._quote(self._urlencode(query_dict))])

    def _parse_error(self, str_as_xml):
        """
        Helper function in order to get error message from an xml string.
        In coming xml can be like this:
        <?xml version='1.0' encoding='UTF-8' standalone='yes'?>
        <error>
         <status>404</status>
         <timestamp>1262186271064</timestamp>
         <error-code>0000</error-code>
         <message>[invalid.property.name]. Couldn't find property with name: first_name</message>
        </error>
        """
        try:
            xmlDocument = minidom.parseString(str_as_xml)
            if len(xmlDocument.getElementsByTagName("error")) > 0:
                error = xmlDocument.getElementsByTagName("message")
                if error:
                    error = error[0]
                    return error.childNodes[0].nodeValue
            return None
        except Exception, detail:
            raise OAuthError("Invalid XML String given: error: %s" % repr(detail))

    ########################
    # END HELPER FUNCTIONS #
    ########################

    def requestToken(self):
        """
        Performs the corresponding API which returns the request token in a query string
        The POST Querydict must include the following:
         * oauth_callback
         * oauth_consumer_key
         * oauth_nonce
         * oauth_signature_method
         * oauth_timestamp
         * oauth_version
        """
        #################
        # BEGIN ROUTINE #
        #################
        # clear everything
        self.clear()
        # initialization
        self.request_oauth_nonce = self._generate_nonce()
        self.request_oauth_timestamp = self._generate_timestamp()
        # create Signature Base String
        method = "POST"
        url = self.getRequestTokenURL()
        query_dict = {"oauth_callback": self.CALLBACK_URL,
                      "oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": self.request_oauth_nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": self.request_oauth_timestamp,
                      "oauth_version": self.version,
                      }
        query_string = self._quote(self._urlencode(query_dict))
        signature_base_string = "&".join([self._quote(method), self._quote(url), query_string])
        # create actual signature
        hashed = hmac.new(self._quote(self.API_SECRET) + "&", signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]
        # it is time to create the heaader of the http request that will be sent
        header = 'OAuth realm="https://rightsignature.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_callback="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (self.request_oauth_nonce, self._quote(self.CALLBACK_URL),
                           self.signature_method, self.request_oauth_timestamp,
                           self._quote(self.API_KEY), self._quote(signature), self.version)


        # next step is to establish an HTTPS connection through the LinkedIn API
        # and fetch the request token.
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, self.REQUEST_TOKEN_URL, body = self._urlencode(query_dict), headers = {'Authorization': header})
        response = connection.getresponse()
        if response is None:
            self.request_oauth_error = "No HTTP response received."
            connection.close()
            return False

        response = response.read()
        connection.close()

        oauth_problem = self._get_value_from_raw_qs("oauth_problem", response)
        if oauth_problem:
            self.request_oauth_error = oauth_problem
            return False

        self.request_token = self._get_value_from_raw_qs("oauth_token", response)
        self.request_token_secret = self._get_value_from_raw_qs("oauth_token_secret", response)
        return True


    def accessToken(self, request_token = None, request_token_secret = None, verifier = None):
        """
        Performs the corresponding API which returns the access token in a query string
        Accroding to the link (http://developer.linkedin.com/docs/DOC-1008), POST Querydict must include the following:
        * oauth_consumer_key
        * oauth_nonce
        * oauth_signature_method
        * oauth_timestamp
        * oauth_token (request token)
        * oauth_version
        """
        #################
        # BEGIN ROUTINE #
        #################
        self.request_token = request_token and request_token or self.request_token
        self.request_token_secret = request_token_secret and request_token_secret or self.request_token_secret
        self.verifier = verifier and verifier or self.verifier
        # if there is no request token, fail immediately
        if self.request_token is None:
            raise OAuthError("There is no Request Token. Please perform 'requestToken' method and obtain that token first.")

        if self.request_token_secret is None:
            raise OAuthError("There is no Request Token Secret. Please perform 'requestToken' method and obtain that token first.")

        if self.verifier is None:
            raise OAuthError("There is no Verifier Key. Please perform 'requestToken' method, redirect user to API authorize page and get the verifier.")

        # initialization
        self.access_oauth_nonce = self._generate_nonce()
        self.access_oauth_timestamp = self._generate_timestamp()

        # create Signature Base String
        method = "POST"
        url = self.getAccessTokenURL()
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": self.access_oauth_nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": self.access_oauth_timestamp,
                      "oauth_token" : self.request_token,
                      "oauth_verifier" : self.verifier,
                      "oauth_version": self.version,
                      }
        query_string = self._quote(self._urlencode(query_dict))
        signature_base_string = "&".join([self._quote(method), self._quote(url), query_string])
        # create actual signature
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.request_token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]
        # it is time to create the heaader of the http request that will be sent
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_verifier="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (self._quote(self.access_oauth_nonce), self._quote(self.signature_method),
                           self.access_oauth_timestamp, self._quote(self.API_KEY),
                           self._quote(self.request_token), self._quote(self.verifier),
                           self._quote(signature), self._quote(self.version))

        # next step is to establish an HTTPS connection through the LinkedIn API
        # and fetch the request token.
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, self.ACCESS_TOKEN_URL, body = self._urlencode(query_dict), headers = {'Authorization': header})
        response = connection.getresponse()
        if response is None:
            self.access_oauth_error = "No HTTP response received."
            connection.close()
            return False

        response = response.read()
        connection.close()
        oauth_problem = self._get_value_from_raw_qs("oauth_problem", response)
        if oauth_problem:
            self.request_oauth_error = oauth_problem
            return False

        self.access_token = self._get_value_from_raw_qs("oauth_token", response)
        self.access_token_secret = self._get_value_from_raw_qs("oauth_token_secret", response)
        return True

    def Get(self, get_path):
        # check the requirements
        if (not self.access_token) or (not self.access_token_secret):
            self.error = "You do not have an access token. Plase perform 'accessToken()' method first."
            raise OAuthError(self.error)

        #################
        # BEGIN ROUTINE #
        #################

        # generate nonce and timestamp
        nonce     = self._generate_nonce()
        timestamp = self._generate_timestamp()

        # create signature and signature base string
        FULL_URL    = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, get_path)
        method      = "GET"
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce"       : nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp"   : timestamp,
                      "oauth_token"       : self.access_token,
                      "oauth_version"     : self.version
                      }

        signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
        hashed                = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, sha)
        signature             = binascii.b2a_base64(hashed.digest())[:-1]

        # create the HTTP header
        header = 'OAuth realm="https://rightsignature.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (nonce, self.signature_method, timestamp,
                           self._quote(self.API_KEY), self._quote(self.access_token),
                           self._quote(signature), self.version)

        # make the request
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, get_path, headers = {'Authorization': header})
        response = connection.getresponse()

        # according to the response, decide what you want to do
        if response is None:
            self.error = "No HTTP response received."
            connection.close()
            return None

        response = response.read()
        connection.close()

                #
                # document = minidom.parseString(response)
                # connections = document.getElementsByTagName("person")
                # result = []
                # for connection in connections:
                #     profile = Profile.create(connection.toxml())
                #     if profile is not None:
                #         result.append(profile)

        ###############
        # END ROUTINE #
        ###############
        return response


    def PostXML(self, post_path, xml_body):

        #######################################################################################
        # BEGIN ROUTINE                                                                       #
        #######################################################################################
        # check the requirements
        if (not self.access_token) or (not self.access_token_secret):
            self.error = "You do not have an access token. Plase perform 'accessToken()' method first."
            raise OAuthError(self.error)



        # Generate nonce and timestamp.
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()

        # create signature and signature base string
        FULL_URL    = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, post_path)
        method      = "POST"
        query_dict  = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": timestamp,
                      "oauth_token" : self.access_token,
                      "oauth_version": self.version
                      }

        signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]

        # Create the HTTP header
        header = 'OAuth realm="https://rightsignature.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (nonce, self.signature_method, timestamp,
                           self._quote(self.API_KEY), self._quote(self.access_token),
                           self._quote(signature), self.version)

        # Make the request
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, post_path, body = xml_body,  headers = {'Authorization': header, "Content-type": "application/xml"})
        response = connection.getresponse()

        response = response.read()
        connection.close()

        return response


    def getRequestTokenError(self):
        return self.request_oauth_error

    def getAccessTokenError(self):
        return self.access_oauth_error

    def getError(self):
        return self.error

    def clear(self):
        self.request_token = None
        self.access_token  = None
        self.verifier      = None

        self.request_token_secret = None
        self.access_token_secret = None

        self.request_oauth_nonce     = None
        self.request_oauth_timestamp = None
        self.access_oauth_nonce      = None
        self.access_oauth_timestamp  = None

        self.request_oauth_error     = None
        self.access_oauth_error      = None
        self.error                   = None

