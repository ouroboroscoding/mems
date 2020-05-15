#
# Copyright notice:
# (c) Copyright 2017 RocketGate
# All rights reserved.
#
# The copyright notice must not be removed without specific, prior
# written permission from RocketGate.
#
# This software is protected as an unpublished work under the U.S. copyright
# laws. The above copyright notice is not intended to effect a publication of
# this work.
# This software is the confidential and proprietary information of RocketGate.
# Neither the binaries nor the source code may be redistributed without prior
# written permission from RocketGate.
#
# The software is provided "as-is" and without warranty of any kind, express, implied
# or otherwise, including without limitation, any warranty of merchantability or fitness
# for a particular purpose.  In no event shall RocketGate be liable for any direct,
# special, incidental, indirect, consequential or other damages of any kind, or any damages
# whatsoever arising out of or in connection with the use or performance of this software,
# including, without limitation, damages resulting from loss of use, data or profits, and
# whether or not advised of the possibility of damage, regardless of the theory of liability.
#
import xml.sax
import http.client
import random
import errno
import socket
import ssl 

class GatewayRequest:

######################################################################
#
#	Define constant hash values.
#
######################################################################
#
    VERSION_INDICATOR = "version"
    VERSION_NUMBER = "PY3.2"

    AFFILIATE = "affiliate"
    AMOUNT = "amount"
    AVS_CHECK = "avsCheck"
    BILLING_ADDRESS = "billingAddress"
    BILLING_CITY = "billingCity"
    BILLING_COUNTRY = "billingCountry"
    BILLING_STATE = "billingState"
    BILLING_TYPE = "billingType"
    BILLING_ZIPCODE = "billingZipCode"
    CARDNO = "cardNo"
    CARD_HASH = "cardHash"
    CURRENCY = "currency"
    CUSTOMER_FIRSTNAME = "customerFirstName"
    CUSTOMER_LASTNAME = "customerLastName"
    CUSTOMER_PHONE_NO = "customerPhoneNo"
    CUSTOMER_PASSWORD = "customerPassword"
    CVV2 = "cvv2"
    CVV2_CHECK = "cvv2Check"
    EMAIL = "email"
    EXPIRE_MONTH = "expireMonth"
    EXPIRE_YEAR = "expireYear"
    IPADDRESS = "ipAddress"
    MERCHANT_ACCOUNT = "merchantAccount"
    MERCHANT_CUSTOMER_ID = "merchantCustomerID"
    MERCHANT_DESCRIPTOR = "merchantDescriptor"
    MERCHANT_INVOICE_ID = "merchantInvoiceID"
    MERCHANT_ID = "merchantID"
    MERCHANT_PASSWORD = "merchantPassword"
    MERCHANT_SITE_ID = "merchantSiteID"
    PARTIAL_AUTH_FLAG = "partialAuthFlag"
    PAY_HASH = "cardHash"
    REBILL_FREQUENCY = "rebillFrequency"
    REBILL_AMOUNT = "rebillAmount"
    REBILL_START = "rebillStart"
    REBILL_END_DATE = "rebillEndDate"
    REFERENCE_GUID = "referenceGUID"
    REFERRING_MERCHANT_ID = "referringMerchantID"
    REFERRED_CUSTOMER_ID = "referredCustomerID"
    SCRUB = "scrub"
    TRANSACT_ID = "referenceGUID"
    TRANSACTION_TYPE = "transactionType"
    UDF01 = "udf01"
    UDF02 = "udf02"
    USERNAME = "username"
    FAILED_SERVER = "failedServer"
    FAILED_GUID = "failedGUID"
    FAILED_RESPONSE_CODE = "failedResponseCode"
    FAILED_REASON_CODE = "failedReasonCode"

    GATEWAY_CONNECT_TIMEOUT = "gatewayConnectTimeout"
    GATEWAY_READ_TIMEOUT = "gatewayReadTimeout"


######################################################################
#
#	__init__() - Constructor for class.
#
######################################################################
#
    def __init__(self):
        self.parameterList = {}
        self.Set(GatewayRequest.VERSION_INDICATOR, \
		 GatewayRequest.VERSION_NUMBER)


######################################################################
#
#	Set() - Set a value in the parameter list.
#
######################################################################
#
    def Set(self, key, value):
        if (key in self.parameterList):		# Have key value?
            del self.parameterList[key]		# Delete it
        self.parameterList[key] = str(value)	# Save the value


######################################################################
#
#	Clear() - Clear a value in the parameter list.
#
######################################################################
#
    def Clear(self, key):
        if (key in self.parameterList):		# Have key value?
            del self.parameterList[key]		# Delete it


######################################################################
#
#	Get() - Get a value from the parameter list.
#
######################################################################
#
    def Get(self, key):
        if (key in self.parameterList):		# Have key value?
            return self.parameterList[key]	# Return the value
        return None				# Don't have a value


######################################################################
#
#	ToXML() - Create an XML document from the hash list.
#
######################################################################
#
    def ToXML(self):

#
#	Build the document header.
#
        xmlDocument = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        xmlDocument += "<gatewayRequest>"

#
#	Loop over each key-value pairs and create
#	and open tag for the key.
#
        for key, value in self.parameterList.items():
            xmlDocument += "<";
            xmlDocument += key
            xmlDocument += ">"

#
#	Clean up the value and add it to the tag.
#
            myValue = str(value)		# In case it's not a string
            myValue = myValue.replace("&", "&amp;");
            myValue = myValue.replace("<", "&lt;");
            myValue = myValue.replace(">", "&gt;");
            xmlDocument += myValue

#
#
#	Add the closing tag for this element.
#
            xmlDocument += "</";
            xmlDocument += key
            xmlDocument += ">"

#
#	Close and return the document.
#
        xmlDocument += "</gatewayRequest>"
        return xmlDocument			# Final document


class GatewayResponse(xml.sax.handler.ContentHandler):

######################################################################
#
#	Define constant hash values.
#
######################################################################
#
    VERSION_INDICATOR = "version"
    AUTH_NO = "authNo"
    AVS_RESPONSE = "avsResponse"
    BALANCE_AMOUNT = "balanceAmount"
    BALANCE_CURRENCY = "balanceCurrency"
    CARD_TYPE = "cardType"
    CARD_HASH = "cardHash"
    CARD_LAST_FOUR = "cardLastFour"
    CARD_EXPIRATION = "cardExpiration"
    CARD_COUNTRY = "cardCountry"
    CARD_REGION = "cardRegion"
    CARD_DEBIT_CREDIT = "cardDebitCredit"
    CARD_DESCRIPTION = "cardDescription"
    CARD_ISSUER_NAME = "cardIssuerName"
    CARD_ISSUER_PHONE = "cardIssuerPhone"
    CARD_ISSUER_URL = "cardIssuerURL"
    CAVV_RESPONSE = "cavvResponse"
    CVV2_CODE = "cvv2Code"
    EXCEPTION = "exception"
    MERCHANT_ACCOUNT = "merchantAccount"
    PAY_TYPE = "payType"
    PAY_HASH = "cardHash"
    PAY_LAST_FOUR = "cardLastFour"
    REASON_CODE = "reasonCode"
    REBILL_END_DATE = "rebillEndDate"
    REBILL_DATE = "rebillDate"
    REBILL_AMOUNT = "rebillAmount"
    RESPONSE_CODE = "responseCode"
    TRANSACT_ID = "guidNo"
    SCRUB_RESULTS = "scrubResults"
    SETTLED_AMOUNT = "approvedAmount"
    SETTLED_CURRENCY = "approvedCurrency"


######################################################################
#
#	__init__() - Constructor for class.
#
######################################################################
#
    def __init__(self):
        self.parameterList = {}			# Fresh list
        self.haveOpenTag = 0			# Haven't seen <gatewayResponse>
        self.valueBuffer = ""			# No value yet
        

######################################################################
#
#	Set() - Set a value in the parameter list.
#
######################################################################
#
    def Set(self, key, value):
        if (key in self.parameterList):         # Have key value?
            del self.parameterList[key]         # Delete it
        self.parameterList[key] = str(value)    # Save the value


######################################################################
#
#	Reset() - Clear all elements in a response.
#
######################################################################
#	
    def Reset(self):
        del self.parameterList			# Kill old list
        self.parameterList = {}			# Start with fresh list


######################################################################
#
#	Get() - Get a value from the parameter list.
#
######################################################################
#
    def Get(self, key):
        if (key in self.parameterList):         # Have key value?
            return self.parameterList[key]      # Return the value
        return None                             # Don't have a value


######################################################################
#
#	SetFromXML() - Set values in a response object
#		       using an XML document.
#
######################################################################
#
    def SetFromXML(self, xmlDocument):

#
#	Initialize the parsing.
#
        self.haveOpenTag = 0			# Haven't tried to open
        self.valueBuffer = ""			# No value yet

#
#	Parse the input string.
#
        try:
            xml.sax.parseString(xmlDocument, self)

#
#	If there was a parsing error, set the error codes
#	and quit.
#
        except xml.sax.SAXException as ex:
            self.Set(GatewayResponse.EXCEPTION, ex.getMessage() + \
                     ": " + xmlDocument)
            self.Set(GatewayResponse.RESPONSE_CODE, 3)
            self.Set(GatewayResponse.REASON_CODE, 400)

#
#	If there was some other type of exception, set the
#	error codes and quit.
#
        except:
            self.Set(GatewayResponse.EXCEPTION, "Unhandled exception: " + \
                     xmlDocument)
            self.Set(GatewayResponse.RESPONSE_CODE, 3)
            self.Set(GatewayResponse.REASON_CODE, 307)


######################################################################
#
#	startElement() - Handler for start of XML element.
#
######################################################################
#
    def startElement(self, name, attrs):
        if (name == "gatewayResponse"):		# Opening of document?
            self.haveOpenTag = 1		# Have seen open tag
        self.valueBuffer = ""			# Start with clean value


######################################################################
#
#	characters() - Handler for element string
#
######################################################################
#
    def characters(self, data):
        if (self.haveOpenTag):			# Seen open yet?
            self.valueBuffer += data


######################################################################
#
#	endElement() - Handler for end of XML element.
#
######################################################################
#
    def endElement(self, name):
        if (name != "gatewayResponse"):		# Opening of document?
            self.Set(name, self.valueBuffer)


class GatewayService:

######################################################################
#
#	Define constants
#
######################################################################
#
    ROCKETGATE_SERVLET = "/gateway/servlet/ServiceDispatcherAccess"
    ROCKETGATE_CONNECT_TIMEOUT = 10
    ROCKETGATE_READ_TIMEOUT = 90
    ROCKETGATE_PORTNO = 443
    ROCKETGATE_USER_AGENT = "RG Client - Python " + str(GatewayRequest.VERSION_NUMBER)

    LIVE_HOST = "gateway.rocketgate.com"
    LIVE_HOST_16 = "gateway-16.rocketgate.com"
    LIVE_HOST_17 = "gateway-17.rocketgate.com"
    TEST_HOST = "dev-gateway.rocketgate.com"


######################################################################
#
#	initialize() - Constructor for class.
#
######################################################################
#
    def __init__(self):
        self.testMode = 0			# Default to live
        self.rocketGateDNS = GatewayService.LIVE_HOST
        self.rocketGateHost = [ GatewayService.LIVE_HOST_16, \
                                GatewayService.LIVE_HOST_17 ]
        self.rocketGateServlet = GatewayService.ROCKETGATE_SERVLET
        self.rocketGatePortNo = GatewayService.ROCKETGATE_PORTNO
        self.rocketGateConnectTimeout = GatewayService.ROCKETGATE_CONNECT_TIMEOUT
        self.rocketGateReadTimeout = GatewayService.ROCKETGATE_READ_TIMEOUT


######################################################################
#
#	SetTestMode() - Select test/development mode.
#
######################################################################
#
    def SetTestMode(self, yesNo):
        if (yesNo):				# Setting test mode?
            self.testMode = 1			# Set to test mode
            del self.rocketGateHost		# Delete old host list
            self.rocketGateHost = [ GatewayService.TEST_HOST ]
            self.rocketGateDNS = GatewayService.TEST_HOST
        else:
            self.testMode = 0			# Set to live mode
            del self.rocketGateHost		# Delete old host list
            self.rocketGateHost = [ GatewayService.LIVE_HOST_16, \
                                    GatewayService.LIVE_HOST_17 ]
            self.rocketGateDNS = GatewayService.LIVE_HOST


######################################################################
#
#	SetHost() - Set the host used by the service
#
######################################################################
#
    def SetHost(self, hostName):
        del self.rocketGateHost			# Delete old host list
        self.rocketGateHost = [ hostName ]	# Use this host
        self.rocketGateDNS = hostName


######################################################################
#
#	SetPortNo() - Set the port number used by the service.
#
######################################################################
#
    def SetPortNo(self, portNo):
        try:
            value = int(portNo)			# Get numeric value
            if (value > 0):			# Have a valid value?
               self.rocketGatePortNo = value
        except:
            pass


######################################################################
#
#	SetServlet() - Set servlet used by the service.
#
######################################################################
#
    def SetServlet(self, servlet):
        self.rocketGateServlet = servlet	# End point


######################################################################
#
#	SetConnectTimeout() - Set connection timeout
#
######################################################################
#
    def SetConnectTimeout(self, timeout):
        try:
            value = int(timeout)		# Get numeric value
            if (value > 0):			# Have a valid value?
               self.rocketGateConnectTimeout = value
        except:
            pass


######################################################################
#
#	SetReadTimeout() - Set read timeout
#
######################################################################
#
    def SetReadTimeout(self, timeout):
        try:
            value = int(timeout)		# Get numeric value
            if (value > 0):			# Have a valid value?
               self.rocketGateReadTimeout = value
        except:
            pass


######################################################################
#
#	SendTransaction() - Send a transaction to a named host.
#			    
######################################################################
#
    def SendTransaction(self, serverName, request, response):

#
#	Gather overrides for transaction.
#
        urlServlet = request.Get("gatewayServlet")
        urlPortNo = request.Get("portNo")

#
#	Determine the final servlet name.
#
        if (urlServlet == None):		# None specified?
            urlServlet = self.rocketGateServlet

#
#	Determine the final port number.
#
        if (urlPortNo == None):
            urlPortNo = self.rocketGatePortNo
        else:
            try:
                value = int(urlPortNo)		# Make sure this is numeric
            except:
                urlPortNo = self.rocketGatePortNo

#
#	Get the connection timeout.
#
        connectTimeout = request.Get("gatewayConnectTimeout")
        if (connectTimeout == None):
            connectTimeout = self.rocketGateConnectTimeout
        else:
            try:
                value = int(connectTimeout)	# Make sure this is numeric
            except:
                connectTimeout = self.rocketGateConnectTimeout

#
#	Get the read timeout.
#
        readTimeout = request.Get("gatewayReadTimeout")
        if (readTimeout == None):
            readTimeout = self.rocketGateReadTimeout
        else:
            try:
                value = int(readTimeout)	# Make sure this is numeric
            except:
                readTimeout = self.rocketGateReadTimeout

#
#	Prepare the values that will go into the post operation.
#
        response.Reset()			# Clear any response data
        requestXML = request.ToXML()		# Get message string
        headers = { "Content-Type": "text/xml", \
                    "User-Agent": GatewayService.ROCKETGATE_USER_AGENT }

#
#	Create the HTTP handler and post our request.
#
        try:
            connection = http.client.HTTPSConnection(serverName, urlPortNo, \
                                                 timeout=connectTimeout)
            connection.request("POST", urlServlet, requestXML, headers)
            connection.sock.settimeout(readTimeout)

#
#	Read the response.
#
            results = connection.getresponse()
            body = results.read()		# Get the response data

#
#	If the response was not '200 OK', we must quit
#
            if (results.status != 200):
                response.Set(GatewayResponse.EXCEPTION, \
                             str(results.status) + ": " + body)
                response.Set(GatewayResponse.RESPONSE_CODE, 3)
                response.Set(GatewayResponse.REASON_CODE, 304)
                return 3			# System error

#
#	If there was a timeout, return an error.
#
        except socket.timeout as ex:
            response.Set(GatewayResponse.EXCEPTION, str(ex))
            response.Set(GatewayResponse.RESPONSE_CODE, 3)
            response.Set(GatewayResponse.REASON_CODE, 301)
            return 3				# System error

#
#	If the read timed out, return an error.
#
        except ssl.SSLError as ex:
            response.Set(GatewayResponse.EXCEPTION, str(ex))
            response.Set(GatewayResponse.RESPONSE_CODE, 3)
            response.Set(GatewayResponse.REASON_CODE, 303)
            return 3				# System error
 
#
#	If there was some other type of socket problemm,
#	return an error.
#
        except socket.error as ex:
            response.Set(GatewayResponse.EXCEPTION, str(ex))
            response.Set(GatewayResponse.RESPONSE_CODE, 3)
            exString = str(ex)
            if ('Connection refused' in exString):
                response.Set(GatewayResponse.REASON_CODE, 301)
            else:
                response.Set(GatewayResponse.REASON_CODE, 304)
            return 3				# System error

#
#	Catch general exceptions.
#
        except Exception as ex:
            response.Set(GatewayResponse.EXCEPTION, str(ex))
            response.Set(GatewayResponse.RESPONSE_CODE, 3)
            response.Set(GatewayResponse.REASON_CODE, 304)
            return 3				# System error

#
#	Other exceptions must be caught too.
#
        except:
            response.Set(GatewayResponse.EXCEPTION, "Unhandled POST exception")
            response.Set(GatewayResponse.RESPONSE_CODE, 3)
            response.Set(GatewayResponse.REASON_CODE, 304)
            return 3				# System error

#
#	Clean up the connection when we are all done.
#
        finally:
            connection.close()			# Done with connection
            
#
#	Parse the response XML and return the response code.
#
        response.SetFromXML(body)		# Set from response body
        responseCode = response.Get(GatewayResponse.RESPONSE_CODE)
        if (responseCode == None):		# Don't have one?
            responseCode = 3			# System error
            response.Set(GatewayResponse.EXCEPTION, body)
            response.Set(GatewayResponse.RESPONSE_CODE, 3)
            response.Set(GatewayResponse.REASON_CODE, 400) 
        return int(responseCode)		# Give back results


######################################################################
#
#	PerformTransaction() - Perform the transaction described
#			       in a gateway request.
#
######################################################################
#
    def PerformTransaction(self, request, response):

#
#	If the request specifies a server name, use it.
#	Otherwise, use the default.
#
        serverName = request.Get("gatewayServer")
        if (serverName != None):		# Override?
            serverList = [ serverName ]		# Use this name
        else:
            serverList = self.rocketGateHost	# Use default list

#
#	Clear any error tracking that may be leftover.
#
        request.Clear(GatewayRequest.FAILED_SERVER)
        request.Clear(GatewayRequest.FAILED_RESPONSE_CODE)
        request.Clear(GatewayRequest.FAILED_REASON_CODE)
        request.Clear(GatewayRequest.FAILED_GUID)

#
#	Randomly pick an endpoint.
#
        if (len(serverList) > 1):		# Have multiples?
            index = random.randint(0, len(serverList)-1)
            if (index > 0):			# Want to change?
                swapper = serverList[0]		# Save the first one
                serverList[0] = serverList[index]
                serverList[index] = swapper	# And swap

#
#	Loop over the hosts and try to send the transaction
#	to each host in the list until it succeeds or fails
#	due to an unrecoverable error.
#
        index = 0				# Start at first position
        while (index < len(serverList)):		# Loop over list
            results = self.SendTransaction(serverList[index], request, response)

#
#	If the transaction was successful, we are done
#
            if (results == 0):			# Success?
                return 1			# All done

#
#	If the transaction is not recoverable, quit.
#
            if (results != 3):			# Unrecoverable?
                return 0			# Must quit

#
#	Save any errors in the response so they can be
# 	transmitted along with the next request.
#
            request.Set(GatewayRequest.FAILED_SERVER, serverList[index])
            request.Set(GatewayRequest.FAILED_RESPONSE_CODE, \
                        response.Get(GatewayResponse.RESPONSE_CODE))
            request.Set(GatewayRequest.FAILED_REASON_CODE, \
                        response.Get(GatewayResponse.REASON_CODE))
            request.Set(GatewayRequest.FAILED_GUID, \
                        response.Get(GatewayResponse.TRANSACT_ID))
            index += 1				# Next index

#
#	If we ran out of places to send this, just quit.
#
        return 0				# Must quit


######################################################################
#
#	PerformTargetedTransaction() - Send a transaction to a
#				       server based upon the GUID.
#
######################################################################
#
    def PerformTargetedTransaction(self, request, response):

#
#	Clear any error tracking that may be leftover.
#
        request.Clear(GatewayRequest.FAILED_SERVER)
        request.Clear(GatewayRequest.FAILED_RESPONSE_CODE)
        request.Clear(GatewayRequest.FAILED_REASON_CODE)
        request.Clear(GatewayRequest.FAILED_GUID)

#
#	This transaction must go to the host that processed a
#	previous referenced transaction.  Get the GUID of the
#	reference transaction.
#
        referenceGUID = request.Get(GatewayRequest.REFERENCE_GUID)
        if (referenceGUID == None):		# Don't have reference?
            response.Set(GatewayResponse.RESPONSE_CODE, 4)
            response.Set(GatewayResponse.REASON_CODE, 410)
            return 0				# And quit

#
#	Strip off the bits that indicate which server should
#	be used.
#
        if (len(referenceGUID) > 15):		# Live servers?
            siteString = referenceGUID[0:2]	# Get first two digits
        else:
            siteString = referenceGUID[0:1]	# Get first digit

#
#	Try to turn the site string into a number.
#
        try:
            siteNo = int(siteString, 16)	# Get site number
        except:					# Parsing error?
            response.Set(GatewayResponse.RESPONSE_CODE, 4)
            response.Set(GatewayResponse.REASON_CODE, 410)
            return 0				# And quit

#
#	Build the hostname to which the transaction should
#	be directed.
#
        serverName = request.Get("gatewayServer")
        if (serverName == None):		# Don't have one?
            serverName = self.rocketGateDNS	# Start with default
            separator = serverName.find(".")	# Find first .
            if (separator > 0):			# Did we find it?
                prefix = serverName[0:separator]
                prefix += "-"			# Add separator
                prefix += str(siteNo)		# Add site number
                prefix += serverName[separator:]# Add the domain information
                serverName = prefix		# Full server name

#
#	Send the transaction to the specified host.
#
        results = self.SendTransaction(serverName, request, response)
        if (results == 0):			# Did server return 0?
            return 1				# This succeeded
        return 0				# This failed


######################################################################
#
#	PerformConfirmation() - Perform the confirmation pass that
#				tells the server we have received
#				the transaction reply.
#
######################################################################
#
    def PerformConfirmation(self, request, response):

#
#	Verify that we have a transaction ID for the
#	confirmation message.
#
        confirmGUID = response.Get(GatewayResponse.TRANSACT_ID)
        if (confirmGUID == None):		# Don't have reference?
            response.Set(GatewayResponse.EXCEPTION, \
                         "BUG-CHECK - Missing confirmation GUID")
            response.Set(GatewayResponse.RESPONSE_CODE, 3)
            response.Set(GatewayResponse.REASON_CODE, 307)
            return 0				# And quit

#
#	Add the GUID to the request and send it back to the
#	original server for confirmation.
#
        confirmResponse = GatewayResponse()	# Need a new response object
        request.Set(GatewayRequest.TRANSACTION_TYPE, "CC_CONFIRM")
        request.Set(GatewayRequest.REFERENCE_GUID, confirmGUID)
        results = self.PerformTargetedTransaction(request, confirmResponse)
        if (results):				# Success?
            return 1				# Yes - We are done

#
#	If the confirmation failed, copy the reason and response code
#	into the original response object to override the success.
#
        response.Set(GatewayResponse.RESPONSE_CODE, \
                     confirmResponse.Get(GatewayResponse.RESPONSE_CODE))
        response.Set(GatewayResponse.REASON_CODE, \
                     confirmResponse.Get(GatewayResponse.REASON_CODE))
        return 0				# And quit


######################################################################
#
#	PerformAuthOnly() - Perform an auth-only transaction.
#
######################################################################
#
    def PerformAuthOnly(self, request, response):
        request.Set(GatewayRequest.TRANSACTION_TYPE, "CC_AUTH")
        results = self.PerformTransaction(request, response)
        if (results):				# Success?
            results = self.PerformConfirmation(request, response)
        return results				# Return results


######################################################################
#
#	PerformTicket() - Perform a Ticket operation for a previous
#			  auth-only transaction.
#
######################################################################
#
    def PerformTicket(self, request, response):
        request.Set(GatewayRequest.TRANSACTION_TYPE, "CC_TICKET")
        results = self.PerformTargetedTransaction(request, response)
        return results				# Return results


######################################################################
#
#	PerformPurchase() - Perform a complete purchase transaction.
#
######################################################################
#
    def PerformPurchase(self, request, response):
        request.Set(GatewayRequest.TRANSACTION_TYPE, "CC_PURCHASE")
        results = self.PerformTransaction(request, response)
        if (results):				# Success?
            results = self.PerformConfirmation(request, response)
        return results				# Return results


######################################################################
#
#	PerformCredit() - Perform a Credit operation for a previous
#			  transaction.
#
######################################################################
#
    def PerformCredit(self, request, response):
        request.Set(GatewayRequest.TRANSACTION_TYPE, "CC_CREDIT")

#
#	If this is a reference GUID, send the transaction to
#	the appropriate server.  Otherwise use the normal
#	transaction distribution.
#
        referenceGUID = request.Get(GatewayRequest.REFERENCE_GUID)
        if (referenceGUID != None):		# Have reference?
            results = self.PerformTargetedTransaction(request, response)
        else:
            results = self.PerformTransaction(request, response)
        return results				# Return results


######################################################################
#
#	PerformVoid() - Perform a Void operation for a previous
#			transaction.
#
######################################################################
#
    def PerformVoid(self, request, response):
        request.Set(GatewayRequest.TRANSACTION_TYPE, "CC_VOID")
        results = self.PerformTargetedTransaction(request, response)
        return results				# Return results


######################################################################
#
#	PerformCardScrub() - Perform scrubbing on a card/customer
#
######################################################################
#
    def PerformCardScrub(self, request, response):
        request.Set(GatewayRequest.TRANSACTION_TYPE, "CARDSCRUB")
        results = self.PerformTransaction(request, response)
        return results				# Return results


######################################################################
#
#	PerformRebillCancel() - Schedule cancellation of rebilling.
#
######################################################################
#
    def PerformRebillCancel(self, request, response):
        request.Set(GatewayRequest.TRANSACTION_TYPE, "REBILL_CANCEL")
        results = self.PerformTransaction(request, response)
        return results				# Return results


######################################################################
#
#	PerformRebillUpdate() - Update terms of a rebilling.
#
######################################################################
#
    def PerformRebillUpdate(self, request, response):
        request.Set(GatewayRequest.TRANSACTION_TYPE, "REBILL_UPDATE")

#
#	If there is no prorated charge, just perform the update.
#
        amount = request.Get(GatewayRequest.AMOUNT)
        if (amount == None):			# No charge?
            results = self.PerformTransaction(request, response)
            return results			# Return results

#
#	If the amount will not result in a chage, just
#	perform the update.
#
        try:					# Check the amount
            value = float(amount)		# Make sure this is valid
            if (value <= 0.0):			# Not chargeable?
                results = self.PerformTransaction(request, response)
                return results			# Return results
        except:					# Not a valid amount
            pass

#
#	If there is a charge, perform the update and confirm
#	the charge.
#
        results = self.PerformTransaction(request, response)
        if (results):				# Success?
            results = self.PerformConfirmation(request, response)
        return results				# Return results

