# coding=utf8
""" Konnektive Service

Handles all Konnektive requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-05-09"

# Python imports
import math
import sys
import urllib.parse

# Pip imports
import requests
from RestOC import Conf, DictHelper, JSON, Services
import xmltodict

# Shared imports
from shared import Rights, USPS

class Konnektive(Services.Service):
	"""Konnektive Service class

	Service for Konnektive CRM access
	"""

	def _generateURL(self, path, params={}):
		"""Generate URL

		Takes a path and params and generates the full URL with query string

		Arguments:
			path (str): The path (without leading/trailing slashes)
			params (dict): Name/value query pairs

		Returns:
			str
		"""

		# Add the user and pass to the params
		params['loginId'] = self._user
		params['password'] = self._pass

		# Generate and return the URL
		return 'https://%s/%s/?%s' % (
			self._host,
			path,
			urllib.parse.urlencode(params)
		)

	def _request(self, path, params):
		"""Request

		Fetches every page of data for a specific query

		Arguments:
			path (str): The path of the http request
			params (dict): The query params for the request

		Returns:
			list
		"""

		# Init the return result and current page
		lRet = []
		iPage = 1

		# Set the results per page
		params['resultsPerPage'] = 200

		# Make sure we get every page
		while(True):

			# Set the current page
			params['page'] = iPage

			# Generate the URL
			sURL = self._generateURL(path, params)

			# Fetch the data
			oRes = requests.post(sURL, headers={"Content-Type": 'application/json; charset=utf-8'})

			# Pull out the data
			dData = oRes.json()

			# If we don't get success
			if dData['result'] != 'SUCCESS':
				break

			# Add the data to the result
			lRet.extend(dData['message']['data'])

			# If we got the last page
			if math.ceil(dData['message']['totalResults'] / 200) == int(dData['message']['page']):
				break

			# Increment the page
			iPage += 1

		# Return the found transactions
		return lRet

	def _post(self, path, params):
		"""Post

		Posts updates that have no return

		Arguments:
			path (str): The path of the http request
			params (dict): The query params for the request

		Returns:
			bool
		"""

		# Generate the URL
		sURL = self._generateURL(path, params)

		# Fetch the data
		oRes = requests.post(sURL, headers={"Content-Type": 'application/json; charset=utf-8'})

		# Pull out the reponse
		dData = oRes.json()

		# Return based on result
		return dData['result'] == 'SUCCESS'

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Store config data
		self._user = Conf.get(('konnektive', 'user'))
		self._pass = Conf.get(('konnektive', 'pass'))
		self._host = Conf.get(('konnektive', 'host'))

		# Store encounter types
		self._encounters = JSON.load('definitions/encounter_by_state.json');

		# Return self for chaining
		return self

	@classmethod
	def install(cls):
		"""Install

		The service's install method, used to setup storage or other one time
		install configurations

		Returns:
			bool
		"""
		return True

	def customer_read(self, data, sesh):
		"""Customer Read

		Fetches a customer's info by ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If detailed flag not passed, don't include
		if 'detailed' not in data:
			data['detailed'] = False

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.READ,
			"ident": data['customerId']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Make the request to Konnektive
		lCustomers = self._request('customer/query', {
			"dateRangeType": "dateCreated",
			"customerId": data['customerId'],
			"startDate": "01/01/2019",
			"endDate": "01/01/3000"
		});

		# If there's none
		if not lCustomers:
			return Services.Response(error=1104)

		# Generate the base data
		dData = {
			"customerId": lCustomers[0]['customerId'],
			"pay": {
				"source": lCustomers[0]['paySource'],
				"type": lCustomers[0]['cardType'],
				"last4": lCustomers[0]['cardLast4'],
				"expires": lCustomers[0]['cardExpiryDate']
			},
			"billing": {
				"address1": lCustomers[0]['address1'],
				"address2": lCustomers[0]['address2'] and lCustomers[0]['address2'].strip() or None,
				"city": lCustomers[0]['city'],
				"company": lCustomers[0]['companyName'] and lCustomers[0]['companyName'].strip() or None,
				"country": lCustomers[0]['country'],
				"firstName": lCustomers[0]['firstName'],
				"lastName": lCustomers[0]['lastName'],
				"postalCode": lCustomers[0]['postalCode'],
				"state": lCustomers[0]['state']
			},
			"created": lCustomers[0]['dateCreated'],
			"email": lCustomers[0]['emailAddress'],
			"phone": lCustomers[0]['phoneNumber'],
			"shipping": {
				"address1": lCustomers[0]['shipAddress1'],
				"address2": lCustomers[0]['shipAddress2'] and lCustomers[0]['shipAddress2'].strip() or None,
				"city": lCustomers[0]['shipCity'],
				"company": lCustomers[0]['shipCompanyName'] and lCustomers[0]['shipCompanyName'].strip() or None,
				"country": lCustomers[0]['shipCountry'],
				"firstName": lCustomers[0]['shipFirstName'],
				"lastName": lCustomers[0]['shipLastName'],
				"postalCode": lCustomers[0]['shipPostalCode'],
				"state": lCustomers[0]['shipState']
			},
			"updated": lCustomers[0]['dateUpdated']
		}

		# If we include extra details
		if data['detailed']:
			dData['notes'] = lCustomers[0]['notes']
			dData['campaign'] = {
				"name": lCustomers[0]['campaignName'],
				"type": lCustomers[0]['campaignType']
			}

		# Return the customer data
		return Services.Response(dData)

	def customer_update(self, data, sesh):
		"""Customer Update

		Updates a customer's demographic data, email, phone, and addresses

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.UPDATE,
			"ident": data['customerId']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Init the params to KNK
		dQuery = {}

		# If the email was passed
		if 'email' in data:
			dQuery['emailAddress'] = data['email']

		# If the phone was passed
		if 'phone' in data:
			dQuery['phoneNumber'] = data['phone']

		# If we got billing info
		if 'billing' in data:

			# Verify it with USPS
			mRes = USPS.address_verify({
				"Address1": data['billing']['address2'],
				"Address2": data['billing']['address1'],
				"City": data['billing']['city'],
				"State": data['billing']['state'],
				"Zip5": data['billing']['postalCode'],
			})

			# If we got a string back, it's an error
			if isinstance(mRes, str):
				return Services.Response(error=(1700, mRes))

			# If we got an error
			if 'Error' in mRes:
				if mRes['Error']['Description'] == 'Address Not Found.':
					return Services.Response(error=1701)
				else:
					return Services.Response(error=(1700, mRes['Error']))

			# Set the values based on the return
			dQuery['firstName'] = not data['billing']['firstName'] and 'NULL' or data['billing']['firstName']
			dQuery['lastName'] = not data['billing']['lastName'] and 'NULL' or data['billing']['lastName']
			dQuery['companyName'] = not data['billing']['company'] and 'NULL' or data['billing']['company']
			dQuery['address1'] = mRes['Address2']
			dQuery['address2'] = 'Address1' in mRes and mRes['Address1'] or 'NULL'
			dQuery['city'] = mRes['City']
			dQuery['state'] = mRes['State']
			dQuery['country'] = 'US'
			dQuery['postalCode'] = mRes['Zip5']

		# If we got shipping info
		if 'shipping' in data:

			# Verify it with USPS
			mRes = USPS.address_verify({
				"Address1": data['shipping']['address2'],
				"Address2": data['shipping']['address1'],
				"City": data['shipping']['city'],
				"State": data['shipping']['state'],
				"Zip5": data['shipping']['postalCode'],
			})

			# If we got a string back, it's an error
			if isinstance(mRes, str):
				return Services.Response(error=(1700, mRes))

			# If we got an error
			if 'Error' in mRes:
				if mRes['Error']['Description'] == 'Address Not Found.':
					return Services.Response(error=1701)
				elif mRes['Error']['Description'] == 'Invalid City.':
					return Services.Response(error=1702)
				else:
					return Services.Response(error=(1700, mRes['Error']))

			# Set the values based on the return
			dQuery['shipFirstName'] = not data['shipping']['firstName'] and 'NULL' or data['shipping']['firstName']
			dQuery['shipLastName'] = not data['shipping']['lastName'] and 'NULL' or data['shipping']['lastName']
			dQuery['shipCompanyName'] = not data['shipping']['company'] and 'NULL' or data['shipping']['company']
			dQuery['shipAddress1'] = mRes['Address2']
			dQuery['shipAddress2'] = 'Address1' in mRes and mRes['Address1'] or 'NULL'
			dQuery['shipCity'] = mRes['City']
			dQuery['shipState'] = mRes['State']
			dQuery['shipCountry'] = 'US'
			dQuery['shipPostalCode'] = mRes['Zip5']

		# If we have something to update
		if dQuery:

			# Add the ID
			dQuery['customerId'] = data['customerId']

			# Send the update to Konnektive
			if not self._post('customer/update', dQuery):
				return Services.Response(error=1103)

		# Return OK
		return Services.Response(True)

	def customerPurchases_read(self, data, sesh):
		"""Customer Purchases

		Fetches purchases for a customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.READ,
			"ident": data['customerId']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Make the request to Konnektive
		lPurchases = self._request('purchase/query', {
			"dateRangeType": "dateCreated",
			"customerId": data['customerId'],
			"sortDir": 0
		});

		# Return what ever's found after removing unnecessary data
		return Services.Response([{
			"billing": {
				"address1": dP['address1'],
				"address2": dP['address2'],
				"city": dP['city'],
				"country": dP['country'],
				"firstName": dP['firstName'],
				"lastName": dP['lastName'],
				"postalCode": dP['postalCode'],
				"state": dP['state']
			},
			"cycleType": dP['billingCycleType'],
			"cycleNumber": dP['billingCycleNumber'],
			"interval": dP['billingIntervalDays'],
			"nextBillDate": dP['nextBillDate'],
			"price": dP['price'],
			"product": dP['productName'],
			"shipping": {
				"address1": dP['shipAddress1'],
				"address2": dP['shipAddress2'],
				"city": dP['shipCity'],
				"country": dP['shipCountry'],
				"firstName": dP['shipFirstName'],
				"lastName": dP['shipLastName'],
				"postalCode": dP['shipPostalCode'],
				"state": dP['shipState']
			},
			"status": dP['status'],
			"totalBilled": dP['totalBilled'],
			"transactions": [{
				"chargeback": dT['isChargedback'] != '0' and {
					"amount": dT['chargebackAmount'],
					"date": dT['chargebackDate'],
					"code": dT['chargebackReasonCode'],
					"note": dT['chargebackNote']
				} or None,
				"date": dT['txnDate'],
				"price": dT['totalAmount'],
				"refunded": dT['amountRefunded'],
				"result": dT['responseType'],
				"response": dT['responseText']
			} for dT in dP['transactions']]
		} for dP in lPurchases])

	def customerOrders_read(self, data, sesh):
		"""Customer Orders

		Fetches the orders for a customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.READ,
			"ident": data['customerId']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# If transactions flag not passed, assume false
		if 'transactions' not in data:
			data['transactions'] = False

		# Make the request to Konnektive
		lOrders = self._request('order/query', {
			"dateRangeType": "dateCreated",
			"customerId": data['customerId'],
			"sortDir": 0
		});

		# If we also want the associated transactions
		if data['transactions']:

			# Get them from this service
			oResponse = self.customerTransactions_read({
				"customerId": data['customerId']
			}, sesh, False)

			# If there's an error
			if oResponse.errorExists():
				return oResponse

			# Store them by order ID
			dTransactions = {}
			for d in oResponse.data[::-1]:

				# If it's an authorize, capture, or sale, store as is
				if d['type'] in ['AUTHORIZE', 'CAPTURE', 'SALE']:
					dTransactions[d['orderId']] = d

				# Else if it's a refund
				elif d['type'] == 'REFUND':
					dTransactions[d['orderId']]['refund'] = '-%s' % d['total']

				elif d['type'] == 'VOID':
					dTransactions[d['orderId']]['voided'] = True

		# Return what ever's found after removing unnecessary data
		return Services.Response([{
			"billing": {
				"address1": dO['address1'],
				"address2": dO['address2'],
				"city": dO['city'],
				"company": dO['companyName'],
				"country": dO['country'],
				"firstName": dO['firstName'],
				"lastName": dO['lastName'],
				"postalCode": dO['postalCode'],
				"state": dO['state']
			},
			"campaign": dO['campaignName'],
			"couponCode": dO['couponCode'],
			"customerId": dO['customerId'],
			"date": dO['dateUpdated'],
			"email": dO['emailAddress'],
			"encounter": dO['state'] and self._encounters[dO['state']] or '',
			"items": 'items' in dO and [{
				"campaign": dI['name'],
				"description": dI['productDescription'],
				"itemId": dI['orderItemId'],
				"price": dI['price'],
				"productId": dI['productId'],
				"shipping": dI['shipping']
			} for dI in dO['items'].values()] or [],
			"orderId": dO['orderId'],
			"phone": dO['phoneNumber'],
			"price": dO['price'],
			"shipping": {
				"address1": dO['shipAddress1'],
				"address2": dO['shipAddress2'],
				"city": dO['shipCity'],
				"company": dO['shipCompanyName'],
				"country": dO['shipCountry'],
				"firstName": dO['shipFirstName'],
				"lastName": dO['shipLastName'],
				"postalCode": dO['shipPostalCode'],
				"state": dO['shipState']
			},
			"status": dO['orderStatus'],
			"type": dO['orderType'],
			"totalAmount": dO['totalAmount'],
			"transactions": (data['transactions'] and dO['orderId'] in dTransactions) and dTransactions[dO['orderId']] or None,
			"currency": dO['currencySymbol']
		} for dO in lOrders])

	def customerTransactions_read(self, data, sesh, verify=True):
		"""Customer Transactions

		Fetches the transactions associated with a specific customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			verify (bool): Allow bypassing verification for internal calls

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		if verify:
			oResponse = Services.read('auth', 'rights/verify', {
				"name": "customers",
				"right": Rights.READ,
				"ident": data['customerId']
			}, sesh)
			if not oResponse.data:
				return Services.Response(error=Rights.INVALID)

		# Make the request to Konnektive
		lTransactions = self._request('transactions/query', {
			"dateRangeType": "dateCreated",
			"customerId": data['customerId'],
			"sortDir": 0
		});

		# Return what ever's found after removing unnecessary data
		return Services.Response([{
			"orderId": d['orderId'],
			"date": d['dateUpdated'],
			"mid": d['merchant'],
			"cycle": d['billingCycleNumber'],
			"recycle": d['recycleNumber'],
			"type": d['txnType'],
			"total": d['totalAmount'],
			"payment": '%s %s' % (d['cardType'], d['cardLast4']),
			"result": d['responseType'],
			"response": d['responseText'],
			"id": d['merchantTxnId'],
			"chargeback": d['isChargedback'] and {
				"amount": d['chargebackAmount'],
				"date": d['chargebackDate'],
				"code": d['chargebackReasonCode'],
				"note": d['chargebackNote']
			} or None,
			"currency": d['currencySymbol']
		} for d in lTransactions])

	def order_read(self, data, sesh):
		"""Order

		Fetches an order by ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['orderId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If transactions flag not passed, assume false
		if 'transactions' not in data:
			data['transactions'] = False

		# Make the request to Konnektive
		dOrder = self._request('order/query', {
			"orderId": data['orderId']
		});

		# If the request is empty
		if not dOrder:
			return Services.Response(error=1104)

		# Set the order to the first item
		dOrder = dOrder[0]

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.READ,
			"ident": dOrder['customerId']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# If we also want the associated transactions
		if data['transactions']:

			# Get them from this service
			oResponse = self.orderTransactions_read({
				"orderId": data['orderId']
			}, sesh, False)

			# If there's an error
			if oResponse.errorExists():
				return oResponse

			# Combine transactions into one record
			dTransaction = {}
			for d in oResponse.data[::-1]:

				# If it's an authorize, capture, or sale, store as is
				if d['type'] in ['AUTHORIZE', 'CAPTURE', 'SALE']:
					dTransaction = d

				# Else if it's a refund
				elif d['type'] == 'REFUND':
					dTransaction['refund'] = '-%s' % d['total']

				elif d['type'] == 'VOID':
					dTransaction['voided'] = True

		# Return the order
		return Services.Response({
			"billing": {
				"address1": dOrder['address1'],
				"address2": dOrder['address2'],
				"city": dOrder['city'],
				"company": dOrder['companyName'],
				"country": dOrder['country'],
				"firstName": dOrder['firstName'],
				"lastName": dOrder['lastName'],
				"postalCode": dOrder['postalCode'],
				"state": dOrder['state']
			},
			"campaign": dOrder['campaignName'],
			"couponCode": dOrder['couponCode'],
			"customerId": dOrder['customerId'],
			"date": dOrder['dateUpdated'],
			"email": dOrder['emailAddress'],
			"encounter": dOrder['state'] and self._encounters[dOrder['state']] or '',
			"items": 'items' in dOrder and [{
				"campaign": dI['name'],
				"description": dI['productDescription'],
				"itemId": dI['orderItemId'],
				"price": dI['price'],
				"productId": dI['productId'],
				"shipping": dI['shipping']
			} for dI in dOrder['items'].values()] or [],
			"orderId": dOrder['orderId'],
			"phone": dOrder['phoneNumber'],
			"price": dOrder['price'],
			"shipping": {
				"address1": dOrder['shipAddress1'],
				"address2": dOrder['shipAddress2'],
				"city": dOrder['shipCity'],
				"company": dOrder['shipCompanyName'],
				"country": dOrder['shipCountry'],
				"firstName": dOrder['shipFirstName'],
				"lastName": dOrder['shipLastName'],
				"postalCode": dOrder['shipPostalCode'],
				"state": dOrder['shipState']
			},
			"status": dOrder['orderStatus'],
			"type": dOrder['orderType'],
			"totalAmount": dOrder['totalAmount'],
			"transactions": data['transactions'] and dTransaction or None,
			"currency": dOrder['currencySymbol']
		})

	def orderQa_update(self, data, sesh):
		"""Order QA

		Marks an order as approved or declined in Konnektive

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Validate rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "orders",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['orderId', 'action'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Uppercase the action
		data['action'] = data['action'].upper()

		# Action must be one of APPROVE or DECLINE
		if data['action'] not in ['APPROVE', 'DECLINE']:
			return Services.Response(error=(1001, [('action', 'invalid')]))

		# Send the update to Konnektive
		#bRes = self._post('customer/update', {
		#	"orderId": data['orderId']
		#})
		bRes = True

		# If we failed
		if not bRes:
			return Services.Response(error=1103)

		# Return OK
		return Services.Response(True)

	def orderTransactions_read(self, data, sesh, verify=True):
		"""Order Transactions

		Fetches the transactions associated with a specific order

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			verify (bool): Allow bypassing verification for internal calls

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['orderId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make the request to Konnektive
		lTransactions = self._request('transactions/query', {
			"dateRangeType": "dateUpdated",
			"orderId": data['orderId'],
			"sortDir": 0
		});

		# If there's no transactions
		if not lTransactions:
			return Services.Response([])

		# Make sure the user has the proper permission to do this
		if verify:
			oResponse = Services.read('auth', 'rights/verify', {
				"name": "customers",
				"right": Rights.READ,
				"ident": lTransactions[0]['customerId']
			}, sesh)
			if not oResponse.data:
				return Services.Response(error=Rights.INVALID)

		# Return what ever's found after removing unnecessary data
		return Services.Response([{
			"date": d['dateUpdated'],
			"mid": d['merchant'],
			"cycle": d['billingCycleNumber'],
			"recycle": d['recycleNumber'],
			"type": d['txnType'],
			"total": d['totalAmount'],
			"payment": '%s %s' % (d['cardType'], d['cardLast4']),
			"result": d['responseType'],
			"response": d['responseText'],
			"id": d['merchantTxnId'],
			"chargeback": d['isChargedback'] and {
				"amount": d['chargebackAmount'],
				"date": d['chargebackDate'],
				"code": d['chargebackReasonCode'],
				"note": d['chargebackNote']
			} or None,
			"currency": d['currencySymbol']
		} for d in lTransactions])
