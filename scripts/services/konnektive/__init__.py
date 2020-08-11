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
from RestOC import Conf, DictHelper, Services
import xmltodict

# Shared imports
from shared import JSON, Rights, USPS

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

	def __post(self, path, params):
		"""Post

		Posts updates that have no return

		Arguments:
			path (str): The path of the http request
			params (dict): The query params for the request

		Returns:
			bool
		"""

		# Generate the URL
		sURL = self.__generateURL(path, params)

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
		self._encounters = JSON.load('../definitions/encounter_by_state.json');

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
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# If detailed flag not passed, don't include
		if 'detailed' not in data:
			data['detailed'] = False

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "crm_customers",
			"right": Rights.READ,
			"ident": data['customerId']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Make the request to Konnektive
		lCustomers = self._request('customer/query', {
			"dateRangeType": "dateCreated",
			"customerId": data['customerId'],
			"startDate": "01/01/2019",
			"endDate": "01/01/3000"
		});

		# If there's none
		if not lCustomers:
			return Services.Effect(error=1104)

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
		return Services.Effect(dData)

	def customer_update(self, data, sesh):
		"""Customer Update

		Updates a customer's demographic data, email, phone, and addresses

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "crm_customers",
			"right": Rights.UPDATE,
			"ident": data['customerId']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

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
				return Services.Effect(error=(1700, mRes))

			# If we got an error
			if 'Error' in mRes:
				if mRes['Error']['Description'] == 'Address Not Found.':
					return Services.Effect(error=1701)
				else:
					return Services.Effect(error=(1700, mRes['Error']))

			# Set the values based on the return
			dQuery['firstName'] = data['billing']['firstName'] == '' and 'NULL' or data['billing']['firstName']
			dQuery['lastName'] = data['billing']['lastName'] == '' and 'NULL' or data['billing']['lastName']
			dQuery['companyName'] = data['billing']['company'] == '' and 'NULL' or data['billing']['company']
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
				return Services.Effect(error=(1700, mRes))

			# If we got an error
			if 'Error' in mRes:
				if mRes['Error']['Description'] == 'Address Not Found.':
					return Services.Effect(error=1701)
				elif mRes['Error']['Description'] == 'Invalid City.':
					return Services.Effect(error=1702)
				else:
					return Services.Effect(error=(1700, mRes['Error']))

			# Set the values based on the return
			dQuery['shipFirstName'] = data['shipping']['firstName'] == '' and 'NULL' or data['shipping']['firstName']
			dQuery['shipLastName'] = data['shipping']['lastName'] == '' and 'NULL' or data['shipping']['lastName']
			dQuery['shipCompanyName'] = data['shipping']['company'] == '' and 'NULL' or data['shipping']['company']
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
			if not self.__post('customer/update', dQuery):
				return Services.Effect(error=1103)

		# Return OK
		return Services.Effect(True)

	def customerPurchases_read(self, data, sesh):
		"""Customer Purchases

		Fetches purchases for a customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "crm_customers",
			"right": Rights.READ,
			"ident": data['customerId']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Make the request to Konnektive
		lPurchases = self.__request('purchase/query', {
			"dateRangeType": "dateCreated",
			"customerId": data['customerId'],
			"sortDir": 0
		});

		# Return what ever's found after removing unnecessary data
		return Services.Effect([{
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
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "crm_customers",
			"right": Rights.READ,
			"ident": data['customerId']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

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
			oEff = self.customerTransactions_read({
				"customerId": data['customerId']
			}, sesh, False)

			# If there's an error
			if oEff.errorExists():
				return oEff

			# Store them by order ID
			dTransactions = {}
			for d in oEff.data[::-1]:

				# If it's an authorize, capture, or sale, store as is
				if d['type'] in ['AUTHORIZE', 'CAPTURE', 'SALE']:
					dTransactions[d['orderId']] = d

				# Else if it's a refund
				elif d['type'] == 'REFUND':
					dTransactions[d['orderId']]['refund'] = '-%s' % d['total']

				elif d['type'] == 'VOID':
					dTransactions[d['orderId']]['voided'] = True

		# Return what ever's found after removing unnecessary data
		return Services.Effect([{
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
			"date": dO['dateUpdated'],
			"email": dO['emailAddress'],
			"encounter": self._encounters[dO['state']],
			"items": 'items' in dO and [{
				"campaign": dI['name'],
				"description": dI['productDescription'],
				"price": dI['price'],
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
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		if verify:
			oEff = Services.read('auth', 'rights/verify', {
				"name": "crm_customers",
				"right": Rights.READ,
				"ident": data['customerId']
			}, sesh)
			if not oEff.data:
				return Services.Effect(error=Rights.INVALID)

		# Make the request to Konnektive
		lTransactions = self._request('transactions/query', {
			"dateRangeType": "dateCreated",
			"customerId": data['customerId'],
			"sortDir": 0
		});

		# Return what ever's found after removing unnecessary data
		return Services.Effect([{
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

	def orderTransactions_read(self, data, sesh):
		"""Order Transactions

		Fetches the transactions associated with a specific customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "crm_customers",
			"right": Rights.READ,
			"ident": data['customerId']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Make the request to Konnektive
		lTransactions = self._request('transactions/query', {
			"dateRangeType": "dateUpdated",
			"customerId": data['customerId'],
			"sortDir": 0
		});

		# Return what ever's found after removing unnecessary data
		return Services.Effect([{
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
