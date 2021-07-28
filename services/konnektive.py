# coding=utf8
""" Konnektive Service

Handles all Konnektive requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-09"

# Python imports
import math
import sys
from time import sleep
import urllib.parse

# Pip imports
import requests
from RestOC import Conf, DictHelper, JSON, Services, StrHelper
import xmltodict

# Records imports
from records.konnektive import Campaign, CampaignProduct

# Shared imports
from shared import Environment, Rights, USPS

# Local imports
from . import emailError

class Konnektive(Services.Service):
	"""Konnektive Service class

	Service for Konnektive CRM access
	"""

	_install = [Campaign, CampaignProduct]
	"""Record types called in install"""

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
		while True:

			# Set the current page
			params['page'] = iPage

			# Generate the URL
			sURL = self._generateURL(path, params)

			# Fetch the data
			iAttempts = 0
			while True:
				try:
					oRes = requests.post(sURL, headers={"Content-Type": 'application/json; charset=utf-8'}, timeout=10)
					break
				except requests.exceptions.ConnectionError as e:
					iAttempts += 1
					if iAttempts < 3:
						sleep(1)
						continue
					raise e
				except requests.exceptions.ReadTimeout as e:
					raise Services.ResponseException(error=1004)

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

		# Send the data
		iAttempts = 0
		while True:
			try:
				oRes = requests.post(sURL, headers={"Content-Type": 'application/json; charset=utf-8'}, timeout=10)
				break
			except requests.exceptions.ConnectionError as e:
				iAttempts += 1
				if iAttempts < 3:
					sleep(1)
					continue
				raise e
			except requests.exceptions.ReadTimeout as e:
				raise Services.ResponseException(error=1004)

		# Pull out the reponse and return it
		return oRes.json()

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
		self._allowQaUpdate = Conf.get(('konnektive', 'allow_qa_update'))
		self._allowPurchaseChange = Conf.get(('konnektive', 'allow_purchase_change'))

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

		# Go through each Record type
		for o in cls._install:

			# Install the table
			if not o.tableCreate():
				print("Failed to create `%s` table" % o.tableName())

		# Return OK
		return True

	def campaign_create(self, data, sesh):
		"""Campaign Create

		Creates a new campaign based on an existing one in Konnektive

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'campaigns', Rights.CREATE)

		# Create a new instance
		try:
			oCampaign = Campaign(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Add the record to the DB and return the ID
		return Services.Response(
			oCampaign.create()
		)

	def campaign_read(self, data, sesh):
		"""Campaign Read

		Fetches and returns an existing campaign

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'campaigns', Rights.READ)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [('_id', 'missing')])

		# Fetch the record
		dCampaign = Campaign.get(data['id'], raw=True)
		if not dCampaign:
			return Services.Error(1104)

		# Return the record
		return Services.Response(dCampaign)

	def campaign_update(self, data, sesh):
		"""Campaign Update

		Updates an existing campaign

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'campaigns', Rights.UPDATE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [('_id', 'missing')])

		# Fetch the record
		oCampaign = Campaign.get(data['id'])
		if not oCampaign:
			return Services.Error(1104)

		# Remove fields that can't change
		for k in ['_id', '_created', '_updated']:
			if k in data:
				del data[k]

		# Go through the remaining fields and attempt to update
		lErrors = []
		for k in data:
			try: oCampaign[k] = data[k]
			except ValueError as e: lErrors.extend(e.args[0])

		# If there was any errors returns them all
		if lErrors:
			return Services.Error(1001, lErrors)

		# Save the record and return the result
		return Services.Response(
			oCampaign.save()
		)

	def campaignProduct_create(self, data, sesh):
		"""Campaign Product Create

		Creates a new campaign product based on an existing one in Konnektive

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'products', Rights.CREATE)

		# Make sure we have a campaign ID
		if 'campaign_id' not in data:
			return Services.Error(1001, [('campaign_id', 'missing')])

		# Make sure the campaign ID is valid
		if not Campaign.exists(data['campaign_id']):
			return Services.Error(1104, 'campaign_id')

		# Create a new instance
		try:
			oProduct = CampaignProduct(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Add the record to the DB and return the ID
		return Services.Response(
			oProduct.create()
		)

	def campaignProduct_delete(self, data, sesh):
		"""Campaign Product Delete

		Deletes an existing campaign product record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'products', Rights.DELETE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [('_id', 'missing')])

		# If the product doesn't exist
		if not CampaignProduct.exists(data['_id']):
			return Services.Error(1104)

		# Delete and return the result
		return Services.Response(
			CampaignProduct.deleteGet(data['_id'])
		)

	def campaignProduct_read(self, data, sesh):
		"""Campaign Create Read

		Fetches and returns an existing campaign product

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'products', Rights.CREATE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [('_id', 'missing')])

		# Fetch the record
		dProduct = CampaignProduct.get(data['id'], raw=True)
		if not dProduct:
			return Services.Error(1104)

		# Return the record
		return Services.Response(dProduct)

	def campaignProduct_update(self, data, sesh):
		"""Campaign Product Update

		Updates an existing campaign product

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'products', Rights.UPDATE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [('_id', 'missing')])

		# Fetch the record
		oProduct = CampaignProduct.get(data['_id'])
		if not oProduct:
			return Services.Error(1104)

		# Remove fields that can't change
		for k in ['_id', 'campaign_id', '_created', '_updated']:
			if k in data:
				del data[k]

		# Go through the remaining fields and attempt to update
		lErrors = []
		for k in data:
			try: oProduct[k] = data[k]
			except ValueError as e: lErrors.extend(e.args[0])

		# If there was any errors returns them all
		if lErrors:
			return Services.Error(1001, lErrors)

		# Save the record and return the result
		return Services.Response(
			oProduct.save()
		)

	def campaignProducts_read(self, data, sesh):
		"""Campaign Products Read

		Fetches and returns all the campaign products in a specific campaign

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'products', Rights.READ)

		# If the Campaign ID is missing
		if 'campaign_id' not in data:
			return Services.Error(1001, [('campaign_id', 'missing')])

		# Find the record
		lProducts = CampaignProduct.filter({
			"campaign_id": data['campaign_id']
		}, raw=True, orderby='name')

		# Return the records
		return Services.Response(lProducts)

	def campaigns_read(self, data, sesh):
		"""Campaigns Read

		Fetches and returns all campaigns

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'campaigns', Rights.READ)

		# Fetch and return the records
		return Services.Response(
			Campaign.get(raw=True, orderby='name')
		)

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
		Rights.check(sesh, 'customers', Rights.READ, data['customerId'])

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
		Rights.check(sesh, 'customers', Rights.UPDATE, data['customerId'])

		# Init the params to KNK
		dQuery = {}

		# If the email was passed
		if 'email' in data:
			dQuery['emailAddress'] = data['email']

		# If the phone was passed
		if 'phone' in data:
			dQuery['phoneNumber'] = StrHelper.digits(data['phone'])[-10:]

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
			dRes = self._post('customer/update', dQuery)

			# If we failed
			if dRes['result'] != 'SUCCESS':
				return Services.Error(1103, ('message' in dRes and dRes['message'] or None))

		# Return OK
		return Services.Response(True)

	def customerPayment_update(self, data, sesh, environ):
		"""Customer Payment

		Updates the payment source for the customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			environ (dict): Environment info related to the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'cc_number', 'cc_expiry', 'cc_cvc'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers', Rights.UPDATE, data['customerId'])

		# Create a fake order to be able to run the card
		oResponse = self.order_create({
			"customerId": data['customerId'],
			"ip": Environment.getClientIP(environ),
			"payment": {
				"type": 'CREDITCARD',
				"number": data['cc_number'],
				"month": data['cc_expiry'][:2],
				"year": data['cc_expiry'][2:],
				"code": data['cc_cvc']
			},
			"campaignId": '139',
			"products": [{
				"id": '994',
				"qty": 1
			}],
			"qa": True
		}, sesh, environ, False)

		# If there's an error
		if oResponse.errorExists():
			return oResponse

		# Cancel the order
		oResponse = self.orderCancel_update({
			"orderId": oResponse.data,
			"reason": "CC Change Order",
			"refund": True
		}, sesh, False)

		# If it failed
		if oResponse.errorExists():
			emailError('CC Change Cancel Order Failed', "Customer: %s\n\nOrder: %s" % (
				str(data['customerId']),
				oResponse.data
			))

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
		Rights.check(sesh, 'customers', Rights.READ, data['customerId'])

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
			"customerId": dP['customerId'],
			"date": dP['dateUpdated'],
			"email": dP['emailAddress'],
			"interval": dP['billingIntervalDays'],
			"nextBillDate": dP['nextBillDate'],
			"phone": dP['phoneNumber'],
			"price": dP['price'],
			"product": {
				"id": dP['productId'],
				"name": dP['productName']
			},
			"purchaseId": dP['purchaseId'],
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
			"shippingPrice": dP['shippingPrice'],
			"status": dP['status'],
			"totalBilled": dP['totalBilled'],
			"transactions": [{
				"chargeback": dT['isChargedback'] != '0' and {
					"amount": 'chargebackAmount' in dT and \
								dT['chargebackAmount'] or \
								('amountRefunded' in dT and \
									dT['amountRefunded'] or \
									'0.00'),
					"date": dT['chargebackDate'],
					"code": dT['chargebackReasonCode'],
					"note": 'chargebackNote' in dT and dT['chargebackNote'] or ''
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
		Rights.check(sesh, 'customers', Rights.READ, data['customerId'])

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
			"campaign": {
				"id": dO['campaignId'],
				"name": dO['campaignName']
			},
			"couponCode": dO['couponCode'],
			"customerId": dO['customerId'],
			"date": dO['dateUpdated'],
			"email": dO['emailAddress'],
			"encounter": (dO['state'] and dO['state'] in self._encounters) and self._encounters[dO['state']] or '',
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
			Rights.check(sesh, 'customers', Rights.READ, data['customerId'])

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

	def order_create(self, data, sesh, environ, verify=True):
		"""Order Create

		Creates a new order

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			environ (dict): Environment info related to the request
			verify (bool): Allow bypassing verification for internal calls

		Returns:
			Services.Response
		"""

		# If we need to verify
		if verify:
			Rights.check(sesh, 'orders', Rights.CREATE)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'campaignId', 'products', 'payment'])
		except ValueError as e: return Services.Error(1001, [(f, 'missing') for f in e.args])

		# If the IP is not sent
		if 'ip' not in data:
			data['ip'] = Environment.getClientIP(environ)

		# Init the data sent to Konnektive
		dData = {}

		# If the pay source is to use the existing
		if data['payment'] == 'existing':
			dData['paySource'] = 'ACCTONFILE'

		# Else, if we got a dictionary
		elif isinstance(data['payment'], dict):

			# Verify pay source fields
			try: DictHelper.eval(data['payment'], ['type', 'number', 'month', 'year', 'code'])
			except ValueError as e: return Services.Error(1001, [('payment.' + f, 'missing') for f in e.args])

			# If the type is not credit card
			if data['payment']['type'] != 'CREDITCARD':
				return Services.Error(1001, [['payment.type', 'invalid']])

			# Add the details
			dData['paySource'] = data['payment']['type']
			dData['cardNumber'] = data['payment']['number']
			dData['cardMonth'] = data['payment']['month']
			dData['cardYear'] = data['payment']['year']
			dData['cardSecurityCode'] = data['payment']['code']

		# Else, invalid paysource
		else:
			return Services.Error(1001, [['payment', 'invalid']])

		# Add the IP address
		dData['ipAddress'] = data['ip']

		# Add the campaign ID
		dData['campaignId'] = data['campaignId']

		# Make sure products is an array
		if isinstance(data['products'], list):

			# Go through each one
			for i in range(len(data['products'])):

				# If it a dictionary
				if isinstance(data['products'][i], dict):

					# Make sure we at least have an ID
					if 'id' not in data['products'][i]:
						return Services.Error(1001, [('paySource.' + f, 'missing') for f in e.args])

					# Product index
					iP = i+1

					# Add the product details
					dData['product%d_id' % iP] = data['products'][i]['id']
					if 'qty' in data['products'][i]:
						dData['product%d_qty' % iP] = data['products'][i]['qty']
					if 'price' in data['products'][i]:
						dData['product%d_price' % iP] = data['products'][i]['price']
					if 'shipping' in data['products'][i]:
						dData['product%d_shipPrice' % iP] = data['products'][i]['shipping']
					if 'variant' in data['products'][i]:
						dData['variant%d_id' % iP] = data['products'][i]['variant']

				# Else, we got invalid data
				else:
					return Services.Error(1001, [['products.%d' % i, 'must be an object']])

		# Else, we got invalid data
		else:
			return Services.Error(1001, [['products', 'must be an array']])

		# If we want to skip QA
		if 'qa' in data and data['qa']:
			dData['forceQA'] = '1'
			dData['skipQA'] = '0'
		else:
			dData['forceQA'] = '0'
			dData['skipQA'] = '1'

		# Init fetch customer data flag
		bFetchCustomer = False

		# If the email or phone is missing
		if 'email' not in data:
			bFetchCustomer = True
		if 'phone' not in data:
			bFetchCustomer = True

		# If the billing info is missing
		if 'billing' not in data or data['billing'] == False:
			bFetchCustomer = True

		# If the shipping info is missing, and it's not meant to be the billing
		#	info
		if 'shipping' not in data or data['shipping'] == False and \
			'shippingIsBilling' not in data or data['shippingIsBilling'] == False:
			bFetchCustomer = True

		# If we need the previous data
		if bFetchCustomer:

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

			# If we need the email
			if 'email' not in data:
				data['email'] = lCustomers[0]['emailAddress']

			# If we need the phone
			if 'phone' not in data:
				data['phone'] = lCustomers[0]['phoneNumber']

			# If we need billing
			if 'billing' not in data or data['billing'] == False:
				data['billing'] = {
					"address1": lCustomers[0]['address1'],
					"address2": lCustomers[0]['address2'],
					"city": lCustomers[0]['city'],
					"company": lCustomers[0]['companyName'],
					"country": lCustomers[0]['country'],
					"firstName": lCustomers[0]['firstName'],
					"lastName": lCustomers[0]['lastName'],
					"postalCode": lCustomers[0]['postalCode'],
					"state": lCustomers[0]['state']
				}

			if 'shipping' not in data or data['shipping'] == False and \
				'shippingIsBilling' not in data or data['shippingIsBilling'] == False:
				data['shipping'] = {
					"address1": lCustomers[0]['shipAddress1'],
					"address2": lCustomers[0]['shipAddress2'],
					"city": lCustomers[0]['shipCity'],
					"company": lCustomers[0]['shipCompanyName'],
					"country": lCustomers[0]['shipCountry'],
					"firstName": lCustomers[0]['shipFirstName'],
					"lastName": lCustomers[0]['shipLastName'],
					"postalCode": lCustomers[0]['shipPostalCode'],
					"state": lCustomers[0]['shipState']
				}

		# Add the email and phone number
		dData['emailAddress'] = data['email']
		dData['phoneNumber'] = data['phone']

		# Verify billing fields
		try: DictHelper.eval(data['billing'], ['address1', 'city', 'country', 'firstName', 'lastName', 'postalCode', 'state'])
		except ValueError as e: return Services.Error(1001, [('billing.' + f, 'missing') for f in e.args])

		# Add the billing info
		dData['address1'] = data['billing']['address1']
		if data['billing']['address2']: dData['address2'] = data['billing']['address2']
		dData['city'] = data['billing']['city']
		if data['billing']['company']: dData['companyName'] = data['billing']['company']
		dData['country'] = data['billing']['country']
		dData['firstName'] = data['billing']['firstName']
		dData['lastName'] = data['billing']['lastName']
		dData['postalCode'] = data['billing']['postalCode']
		dData['state'] = data['billing']['state']

		# If we need shipping info
		if 'shippingIsBilling' not in data or data['shippingIsBilling'] == False:

			# Verify shipping fields
			try: DictHelper.eval(data['shipping'], ['address1', 'city', 'country', 'firstName', 'lastName', 'postalCode', 'state'])
			except ValueError as e: return Services.Error(1001, [('shipping.' + f, 'missing') for f in e.args])

			dData['shipAddress1'] = data['shipping']['address1']
			if data['shipping']['address2']: dData['shipAddress2'] = data['shipping']['address2']
			dData['shipCity'] = data['shipping']['city']
			if data['shipping']['company']: dData['shipCompanyName'] = data['shipping']['company']
			dData['shipCountry'] = data['shipping']['country']
			dData['shipFirstName'] = data['shipping']['firstName']
			dData['shipLastName'] = data['shipping']['lastName']
			dData['shipPostalCode'] = data['shipping']['postalCode']
			dData['shipState'] = data['shipping']['state']
		else:
			dData['billShipSame'] = '1'

		# Send the order to konnektice
		dRes = self._post('order/import', dData)

		# If we we successful
		if dRes['result'] == 'SUCCESS':

			# Return the orderId
			return Services.Response(dRes['message']['orderId'])

		# else, we failed
		else:

			# Return the message from konnektive
			return Services.Error(1100, dRes['message'])

	def order_read(self, data, sesh, environ):
		"""Order Read

		Fetches an order by ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			environ (dict): Environment info related to the request

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
		Rights.check(sesh, 'customers', Rights.READ, dOrder['customerId'])

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
			"campaign": {
				"id": dOrder['campaignId'],
				"name": dOrder['campaignName']
			},
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

	def orderCancel_update(self, data, sesh, verify=True):
		"""Order Cancel

		Cancels an order and optionally issues a full refund

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			verify (bool): Allow bypassing verification for internal calls

		Returns:
			Services.Response
		"""

		# Validate rights
		if verify:
			Rights.check(sesh, 'orders', Rights.UPDATE)

		# Verify fields
		try: DictHelper.eval(data, ['orderId', 'reason'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Init data to send
		dData = {
			"orderId": data['orderId'],
			"cancelReason": data['reason']
		}

		# If refund was passed
		if 'refund' in data and data['refund']:
			dData['fullRefund'] = 'true'

		# Make the request
		dRes = self._post('order/cancel', dData)

		# If we failed
		if dRes['result'] != 'SUCCESS':
			return Services.Error(1103, ('message' in dRes and dRes['message'] or None))

		# Return OK
		return Services.Response(True)

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
		Rights.check(sesh, 'orders', Rights.UPDATE)

		# Verify fields
		try: DictHelper.eval(data, ['orderId', 'action'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Uppercase the action
		data['action'] = data['action'].upper()

		# Action must be one of APPROVE or DECLINE
		if data['action'] not in ['APPROVE', 'DECLINE']:
			return Services.Response(error=(1001, [('action', 'invalid')]))

		# If QA updates are allowed
		if self._allowQaUpdate:

			# Send the update to Konnektive
			dRes = self._post('order/qa', {
				"action": data['action'],
				"orderId": data['orderId']
			})

			# If we failed
			if dRes['result'] != 'SUCCESS':
				return Services.Error(1103, ('message' in dRes and dRes['message'] or None))

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
			Rights.check(sesh, 'customers', Rights.READ, lTransactions[0]['customerId'])

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

	def purchase_read(self, data, sesh):
		"""Purchase read

		Returns data on one specific purchase

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers', Rights.READ)

		# Verify fields
		try: DictHelper.eval(data, ['purchaseId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make the request to Konnektive
		dPurchase = self._request('purchase/query', {
			"purchaseId": data['purchaseId']
		});

		# If the request is empty
		if not dPurchase:
			return Services.Response(error=1104)

		# Set the purchase to the first item
		dPurchase = dPurchase[0]

		# Return what ever's found after removing unnecessary data
		return Services.Response({
			"billing": {
				"address1": dPurchase['address1'],
				"address2": dPurchase['address2'],
				"city": dPurchase['city'],
				"country": dPurchase['country'],
				"firstName": dPurchase['firstName'],
				"lastName": dPurchase['lastName'],
				"postalCode": dPurchase['postalCode'],
				"state": dPurchase['state']
			},
			"cycleType": dPurchase['billingCycleType'],
			"cycleNumber": dPurchase['billingCycleNumber'],
			"customerId": dPurchase['customerId'],
			"date": dPurchase['dateUpdated'],
			"email": dPurchase['emailAddress'],
			"interval": dPurchase['billingIntervalDays'],
			"nextBillDate": dPurchase['nextBillDate'],
			"phone": dPurchase['phoneNumber'],
			"price": dPurchase['price'],
			"product": {
				"id": dPurchase['productId'],
				"name": dPurchase['productName']
			},
			"purchaseId": dPurchase['purchaseId'],
			"shipping": {
				"address1": dPurchase['shipAddress1'],
				"address2": dPurchase['shipAddress2'],
				"city": dPurchase['shipCity'],
				"country": dPurchase['shipCountry'],
				"firstName": dPurchase['shipFirstName'],
				"lastName": dPurchase['shipLastName'],
				"postalCode": dPurchase['shipPostalCode'],
				"state": dPurchase['shipState']
			},
			"shippingPrice": dPurchase['shippingPrice'],
			"status": dPurchase['status'],
			"totalBilled": dPurchase['totalBilled'],
			"transactions": [{
				"chargeback": dT['isChargedback'] != '0' and {
					"amount": 'chargebackAmount' in dT and \
								dT['chargebackAmount'] or \
								('amountRefunded' in dT and \
									dT['amountRefunded'] or \
									'0.00'),
					"date": dT['chargebackDate'],
					"code": dT['chargebackReasonCode'],
					"note": 'chargebackNote' in dT and dT['chargebackNote'] or ''
				} or None,
				"date": dT['txnDate'],
				"price": dT['totalAmount'],
				"refunded": dT['amountRefunded'],
				"result": dT['responseType'],
				"response": dT['responseText']
			} for dT in dPurchase['transactions']]
		})

	def purchaseCancel_update(self, data, sesh):
		"""Purchase Cancel

		Stops a purchase (subscription) in Konnektive so that the customer
		will stop being billed at intervals

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Validate rights
		Rights.check(sesh, 'orders', Rights.UPDATE)

		# Verify fields
		try: DictHelper.eval(data, ['purchaseId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Init the data sent to Konnektive
		dData = {
			"purchaseId": data['purchaseId']
		}

		# If a reason was passed
		if 'reason' in data:
			dData['reason'] = data['reason']

		# If Purchase changes are allowed
		if self._allowPurchaseChange:

			# Cancel the purchase
			dRes = self._post('purchase/cancel', dData)

			# If we failed
			if dRes['result'] != 'SUCCESS':
				return Services.Error(1103, ('message' in dRes and dRes['message'] or None))

		# Return OK
		return Services.Response(True)

	def purchaseCharge_update(self, data, sesh):
		"""Purchase Charge

		Charges the purchase immediately

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Validate rights
		Rights.check(sesh, 'orders', Rights.UPDATE)

		# Verify fields
		try: DictHelper.eval(data, ['purchaseId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If Purchase changes are allowed
		if self._allowPurchaseChange:

			# Cancel the purchase
			dRes = self._post('purchase/cancel', {
				"billNow": True,
				"purchaseId": data['purchaseId']
			})

			# If we failed
			if dRes['result'] != 'SUCCESS':
				return Services.Error(1103, ('message' in dRes and dRes['message'] or None))

		# Return OK
		return Services.Response(True)
