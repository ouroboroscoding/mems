# coding=utf8
""" Payment Service

Handles all Payment requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-05-10"

# Python imports
import re

# Pip imports
from RestOC import Conf, DictHelper, Errors, Services

# Shared imports
from shared import JSON

# Service imports
from .records import Customer
from .RocketGate import *

class Payment(Services.Service):
	"""Payment Service class

	Service for Payment access

	Extends: shared.Services.Service
	"""

	_customer_regex = re.compile('^[a-zA-Z0-9_-]{6,32}$')
	"""Customer ID regular expression"""

	_billing_fields = [
		'cc', 'cc_expire_month', 'cc_expire_year', 'cvv2', 'first_name',
		'last_name', 'address', 'city', 'division', 'postal_code', 'country',
		'ip_address', 'email'
	]
	"""Data to check for if card hash isn't passed / we don't have a customer"""

	_install = [Customer]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Store config data
		self._merchant_id = Conf.get(('rocketgate', 'merchant_id'))
		self._merchant_pass = Conf.get(('rocketgate', 'merchant_pass'))
		self._test_mode = Conf.get(('rocketgate', 'test_mode'), True)

		# Load RocketGate errors file
		self._error_codes = JSON.load('../definitions/rocketgate_errors.json')

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

	def auth_create(self, data):
		"""Authorize

		Check for funds

		Arguments:
			data {mixed} -- Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_internal_', 'amount', 'customer_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		#if not Services.internalKey(data['_internal_']):
		#	return Services.Effect(error=Errors.SERVICE_INTERNAL_KEY)
		#del data['_internal_']

		# Make sure the customer ID is valid before doing anything
		if not self._customer_regex.match(data['customer_id']):
			return Services.Effect(error=1700)

		# Create a RG service instance
		oService = GatewayService()

		# Create a RG request instance
		oRequest = GatewayRequest()
		oRequest.Set(GatewayRequest.MERCHANT_ID, self._merchant_id)
		oRequest.Set(GatewayRequest.MERCHANT_PASSWORD, self._merchant_pass)
		oRequest.Set(GatewayRequest.MERCHANT_CUSTOMER_ID, data['customer_id'])

		# If we're in test mode, turn it on and ignore scrubbing
		if self._test_mode:
			oService.SetTestMode(1)
			oRequest.Set(GatewayRequest.SCRUB, "IGNORE")

		# Look for the customer
		oCustomer = Customer.get(data['customer_id'])

		# If we don't have one, we better have the billing info
		if not oCustomer or 'billing' in data:

			# Verify existence of billing fields
			if 'billing' not in data: return Services.Effect(error=(1001, [('billing', 'missing')]))
			try: DictHelper.eval(data['billing'], self._billing_fields)
			except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

			# Add all the fields
			oRequest.Set(GatewayRequest.CARDNO, data['billing']['cc'])
			oRequest.Set(GatewayRequest.EXPIRE_MONTH, data['billing']['cc_expire_month'])
			oRequest.Set(GatewayRequest.EXPIRE_YEAR, data['billing']['cc_expire_year'])
			oRequest.Set(GatewayRequest.CUSTOMER_FIRSTNAME, data['billing']['first_name'])
			oRequest.Set(GatewayRequest.CUSTOMER_LASTNAME, data['billing']['last_name'])
			oRequest.Set(GatewayRequest.BILLING_ADDRESS, data['billing']['address'])
			oRequest.Set(GatewayRequest.BILLING_CITY, data['billing']['city'])
			oRequest.Set(GatewayRequest.BILLING_STATE, data['billing']['division'])
			oRequest.Set(GatewayRequest.BILLING_ZIPCODE, data['billing']['postal_code'])
			oRequest.Set(GatewayRequest.BILLING_COUNTRY, data['billing']['country'])
			oRequest.Set(GatewayRequest.CVV2, data['billing']['cvv2'])
			oRequest.Set(GatewayRequest.AVS_CHECK, "YES")
			oRequest.Set(GatewayRequest.CVV2_CHECK, "YES")

			# Add optional
			if 'email' in data['billing']:
				oRequest.Set(GatewayRequest.EMAIL, data['billing']['email'])
			if 'phone' in data['billing']:
				oRequest.Set(GatewayRequest.CUSTOMER_PHONE_NO, data['billing']['phone'])
			if 'ip_address' in data['billing']:
				oRequest.Set(GatewayRequest.IPADDRESS, data['billing']['ip_address'])

		# Else, use the card hash
		else:
			oRequest.Set(GatewayRequest.CARD_HASH, oCustomer['card_hash'])

		# Set the amount
		oRequest.Set(GatewayRequest.AMOUNT, 10.97)

		# Create a RG response instance
		oResponse = GatewayResponse()

		# Run the authorize
		bSuccess = oService.PerformAuthOnly(oRequest, oResponse)

		# If the transaction failed
		if not bSuccess:

			# Return an error
			return Services.Effect(error=(1701, {
				"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
				"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
				"responde_msg": oResponse.Get(GatewayResponse.RESPONSE_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.RESPONSE_CODE)] or \
								"unknown response",
				"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
				"reason_msg": oResponse.Get(GatewayResponse.REASON_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.REASON_CODE)] or \
								"unknown reason",
				"exception": oResponse.Get(GatewayResponse.EXCEPTION)
			}))

			print ("Auth-Only failed")
			print ("Scrub:", oResponse.Get(GatewayResponse.SCRUB_RESULTS))

			# Return Failure
			return Services.Effect(False)

		# If there's no customer
		if not oCustomer:

			# Create the new instance
			oCustomer = Customer({
				"_id": data['customer_id'],
				"card_hash": oResponse.Get(GatewayResponse.CARD_HASH)
			})

			# Add it to the DB
			oCustomer.create()

		# Else if we have billing info, update the hash
		elif 'billing' in data:
			oCustomer['card_hash'] = oResponse.Get(GatewayResponse.CARD_HASH)
			oCustomer.save()

		print ("Auth-Only success")
		print ("CVV2:", oResponse.Get(GatewayResponse.CVV2_CODE))
		print ("CardHash:", oResponse.Get(GatewayResponse.CARD_HASH))
		print ("Scrub:", oResponse.Get(GatewayResponse.SCRUB_RESULTS))

		# Return Success
		return Services.Effect({
			"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
			"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
			"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
			"auth_no": oResponse.Get(GatewayResponse.AUTH_NO),
			"avs_response": oResponse.Get(GatewayResponse.AVS_RESPONSE),
			"mid": oResponse.Get(GatewayResponse.MERCHANT_ACCOUNT),
			"scrub": oResponse.Get(GatewayResponse.SCRUB_RESULTS)
		})

	def credit_create(self, data):
		"""Credit

		Credits a previous transaction

		Arguments:
			data {mixed} -- Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_internal_', 'transaction_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		#if not Services.internalKey(data['_internal_']):
		#	return Services.Effect(error=Errors.SERVICE_INTERNAL_KEY)
		#del data['_internal_']

		# Create a RG service instance
		oService = GatewayService()

		# If we're in test mode, turn it on
		if self._test_mode:
			oService.SetTestMode(1)

		# Create a RG request instance
		oRequest = GatewayRequest()
		oRequest.Set(GatewayRequest.MERCHANT_ID, self._merchant_id)
		oRequest.Set(GatewayRequest.MERCHANT_PASSWORD, self._merchant_pass)
		oRequest.Set(GatewayRequest.TRANSACT_ID, data['transaction_id'])

		# Create a RG response instance
		oResponse = GatewayResponse()

		# Credit an existing transaction
		bSuccess = oService.PerformCredit(oRequest, oResponse)

		# If the transaction failed
		if not bSuccess:

			# Return an error
			return Services.Effect(error=(1701, {
				"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
				"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
				"responde_msg": oResponse.Get(GatewayResponse.RESPONSE_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.RESPONSE_CODE)] or \
								"unknown response",
				"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
				"reason_msg": oResponse.Get(GatewayResponse.REASON_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.REASON_CODE)] or \
								"unknown reason",
				"exception": oResponse.Get(GatewayResponse.EXCEPTION)
			}))

		# Return Success
		return Services.Effect({
			"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
			"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
			"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
			"auth_no": oResponse.Get(GatewayResponse.AUTH_NO)
		})

	def capture_create(self, data):
		"""Capture

		Captures a previous authrization

		Arguments:
			data {mixed} -- Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_internal_', 'transaction_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		#if not Services.internalKey(data['_internal_']):
		#	return Services.Effect(error=Errors.SERVICE_INTERNAL_KEY)
		#del data['_internal_']

		# Create a RG service instance
		oService = GatewayService()

		# If we're in test mode, turn it on
		if self._test_mode:
			oService.SetTestMode(1)

		# Create a RG request instance
		oRequest = GatewayRequest()
		oRequest.Set(GatewayRequest.MERCHANT_ID, self._merchant_id)
		oRequest.Set(GatewayRequest.MERCHANT_PASSWORD, self._merchant_pass)
		oRequest.Set(GatewayRequest.TRANSACT_ID, data['transaction_id'])

		# Create a RG response instance
		oResponse = GatewayResponse()

		# Make the capture on the existing transaction
		bSuccess = oService.PerformTicket(oRequest, oResponse)

		# If the transaction failed
		if not bSuccess:

			# Return an error
			return Services.Effect(error=(1701, {
				"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
				"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
				"responde_msg": oResponse.Get(GatewayResponse.RESPONSE_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.RESPONSE_CODE)] or \
								"unknown response",
				"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
				"reason_msg": oResponse.Get(GatewayResponse.REASON_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.REASON_CODE)] or \
								"unknown reason",
				"exception": oResponse.Get(GatewayResponse.EXCEPTION)
			}))

		# Return Success
		return Services.Effect({
			"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
			"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
			"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
			"auth_no": oResponse.Get(GatewayResponse.AUTH_NO)
		})

	def sale_create(self, data):
		"""Sale

		Immediately captures funds (if available)

		Arguments:
			data {mixed} -- Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_internal_', 'amount', 'customer_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		#if not Services.internalKey(data['_internal_']):
		#	return Services.Effect(error=Errors.SERVICE_INTERNAL_KEY)
		#del data['_internal_']

		# Make sure the customer ID is valid before doing anything
		if not self._customer_regex.match(data['customer_id']):
			return Services.Effect(error=1700)

		# Create a RG service instance
		oService = GatewayService()

		# Create a RG request instance
		oRequest = GatewayRequest()
		oRequest.Set(GatewayRequest.MERCHANT_ID, self._merchant_id)
		oRequest.Set(GatewayRequest.MERCHANT_PASSWORD, self._merchant_pass)
		oRequest.Set(GatewayRequest.MERCHANT_CUSTOMER_ID, data['customer_id'])

		# If we're in test mode, turn it on and ignore scrubbing
		if self._test_mode:
			oService.SetTestMode(1)
			oRequest.Set(GatewayRequest.SCRUB, "IGNORE")

		# Look for the customer
		oCustomer = Customer.get(data['customer_id'])

		# If we don't have one, we better have the billing info
		if not oCustomer or 'billing' in data:

			# Verify existence of billing fields
			if 'billing' not in data: return Services.Effect(error=(1001, [('billing', 'missing')]))
			try: DictHelper.eval(data['billing'], self._billing_fields)
			except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

			# Add all the fields
			oRequest.Set(GatewayRequest.CARDNO, data['billing']['cc'])
			oRequest.Set(GatewayRequest.EXPIRE_MONTH, data['billing']['cc_expire_month'])
			oRequest.Set(GatewayRequest.EXPIRE_YEAR, data['billing']['cc_expire_year'])
			oRequest.Set(GatewayRequest.CUSTOMER_FIRSTNAME, data['billing']['first_name'])
			oRequest.Set(GatewayRequest.CUSTOMER_LASTNAME, data['billing']['last_name'])
			oRequest.Set(GatewayRequest.BILLING_ADDRESS, data['billing']['address'])
			oRequest.Set(GatewayRequest.BILLING_CITY, data['billing']['city'])
			oRequest.Set(GatewayRequest.BILLING_STATE, data['billing']['division'])
			oRequest.Set(GatewayRequest.BILLING_ZIPCODE, data['billing']['postal_code'])
			oRequest.Set(GatewayRequest.BILLING_COUNTRY, data['billing']['country'])
			oRequest.Set(GatewayRequest.CVV2, data['billing']['cvv2'])
			oRequest.Set(GatewayRequest.AVS_CHECK, "YES")
			oRequest.Set(GatewayRequest.CVV2_CHECK, "YES")

			# Add optional
			if 'email' in data['billing']:
				oRequest.Set(GatewayRequest.EMAIL, data['billing']['email'])
			if 'phone' in data['billing']:
				oRequest.Set(GatewayRequest.CUSTOMER_PHONE_NO, data['billing']['phone'])
			if 'ip_address' in data['billing']:
				oRequest.Set(GatewayRequest.IPADDRESS, data['billing']['ip_address'])

		# Else, use the card hash
		else:
			oRequest.Set(GatewayRequest.CARD_HASH, oCustomer['card_hash'])

		# Set the amount
		oRequest.Set(GatewayRequest.AMOUNT, 10.97)

		# Create a RG response instance
		oResponse = GatewayResponse()

		# Make the sale
		bSuccess = oService.PerformPurchase(oRequest, oResponse)

		# If the transaction failed
		if not bSuccess:

			# Return an error
			return Services.Effect(error=(1701, {
				"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
				"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
				"responde_msg": oResponse.Get(GatewayResponse.RESPONSE_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.RESPONSE_CODE)] or \
								"unknown response",
				"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
				"reason_msg": oResponse.Get(GatewayResponse.REASON_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.REASON_CODE)] or \
								"unknown reason",
				"exception": oResponse.Get(GatewayResponse.EXCEPTION)
			}))

		# If there's no customer
		if not oCustomer:

			# Create the new instance
			oCustomer = Customer({
				"_id": data['customer_id'],
				"card_hash": oResponse.Get(GatewayResponse.CARD_HASH)
			})

			# Add it to the DB
			oCustomer.create()

		# Else if we have billing info, update the hash
		elif 'billing' in data:
			oCustomer['card_hash'] = oResponse.Get(GatewayResponse.CARD_HASH)
			oCustomer.save()

		print ("Purchase succeeded")
		print ("CVV2:", oResponse.Get(GatewayResponse.CVV2_CODE))
		print ("CardHash:", oResponse.Get(GatewayResponse.CARD_HASH))
		print ("Scrub:", oResponse.Get(GatewayResponse.SCRUB_RESULTS))

		# Return Success
		return Services.Effect({
			"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
			"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
			"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
			"auth_no": oResponse.Get(GatewayResponse.AUTH_NO),
			"avs_response": oResponse.Get(GatewayResponse.AVS_RESPONSE),
			"mid": oResponse.Get(GatewayResponse.MERCHANT_ACCOUNT),
			"scrub": oResponse.Get(GatewayResponse.SCRUB_RESULTS)
		})

	def void_create(self, data):
		"""Void

		Voids a previous Authorize transaction

		Arguments:
			data {mixed} -- Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_internal_', 'transaction_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		#if not Services.internalKey(data['_internal_']):
		#	return Services.Effect(error=Errors.SERVICE_INTERNAL_KEY)
		#del data['_internal_']

		# Create a RG service instance
		oService = GatewayService()

		# If we're in test mode, turn it on
		if self._test_mode:
			oService.SetTestMode(1)

		# Create a RG request instance
		oRequest = GatewayRequest()
		oRequest.Set(GatewayRequest.MERCHANT_ID, self._merchant_id)
		oRequest.Set(GatewayRequest.MERCHANT_PASSWORD, self._merchant_pass)
		oRequest.Set(GatewayRequest.TRANSACT_ID, data['transaction_id'])

		# Create a RG response instance
		oResponse = GatewayResponse()

		# Void an existing transaction
		bSuccess = oService.PerformVoid(oRequest, oResponse)

		# If the transaction failed
		if not bSuccess:

			# Return an error
			return Services.Effect(error=(1701, {
				"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
				"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
				"responde_msg": oResponse.Get(GatewayResponse.RESPONSE_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.RESPONSE_CODE)] or \
								"unknown response",
				"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
				"reason_msg": oResponse.Get(GatewayResponse.REASON_CODE) in self._error_codes and \
								self._error_codes[oResponse.Get(GatewayResponse.REASON_CODE)] or \
								"unknown reason",
				"exception": oResponse.Get(GatewayResponse.EXCEPTION)
			}))

		# Return Success
		return Services.Effect({
			"transaction_id": oResponse.Get(GatewayResponse.TRANSACT_ID),
			"response_code": oResponse.Get(GatewayResponse.RESPONSE_CODE),
			"reason_code": oResponse.Get(GatewayResponse.REASON_CODE),
			"auth_no": oResponse.Get(GatewayResponse.AUTH_NO)
		})
