# coding=utf8
""" Payments Service

Handles all requests to charge Payments with Mids/Gateways
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-04-08"

# Python imports
import re

# Pip imports
from RestOC import Conf, Errors, Services
from FormatOC import Parent, Tree

# Service imports
from .records import Merchant, VaultCustomer
from . import nmi

# Psuedo Switch
GATEWAYS = {
	"nmi": nmi
}

# CC Regular expressions
reCC = re.compile(
	r'^(?:' +
		r'4[0-9]{12}(?:[0-9]{3})?|' +		# Visa
		r'(?:5[1-5][0-9]{2}|' +				# MasterCard
		r'222[1-9]|22[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}|' +
		r'3[47][0-9]{13}|' +				# American Express
		r'3(?:0[0-5]|[68][0-9])[0-9]{11}|' +# Diners Club
		r'6(?:011|5[0-9]{2})[0-9]{12}|' +	# Discover
		r'|(?:2131|1800|35\d{3})\d{11}' +	# JCB
	r')$'
)
reCVV = re.compile(r'^\d{3,4}$')
reEXP = re.compile(r'^[01]\d{3}')

TransactionValidation = Parent({
	"amount": "price",
	"customer": "uint",
	"merchant": "uint",
	"order": "uint",
})
"""Transaction Validation

Used to verify requests have the right data"""

VaultValidation = Tree({
	"__name__": "vault",
	"cc": {"__type__": "string", "__regex__": reCC},
	"exp": {"__type__": "string", "__regex__": reEXP},
	"cvv": {"__type__": "string", "__regex__": reCVV},
	"firstName": {"__type__": "string", "__minimum__": 1},
	"lastName": {"__type__": "string", "__minimum__": 2},
	"address1": {"__type__": "string", "__minimum__": 1},
	"address2": {"__type__": "string", "__optional__": True},
	"city": {"__type__": "string", "__minimum__": 1},
	"division": {"__type__": "string", "__minimum__": 1},
	"country": {"__type__": "string", "__regex__": "^[A-Z]{2}$"},
	"postal": {"__type__": "string", "__minimum__": 5},
	"phone": {"__type__": "string", "__regex__": r"^\d{10,}$"},
	"ip": {"__type__": "ip"}
})

class Payments(Services.Service):
	"""Payments Service class

	Service for charging customers

	Extends: shared.Services.Service
	"""

	_install = [Merchant, VaultCustomer]
	"""Record types called in install"""

	def _checkCustomer(self, customer, merchant, details):
		"""Check Customer

		Checks if we have an account with the customer in the given
		merchant/gateway, if not we fetch the details and create it

		Arguments:
			data {dict} -- The data from the calling request

		Returns:
			dict

		Raises:
			EffectException
		"""

		# Init the return
		dRet = {
			"params": {}
		}

		# Fetch the merchant
		dMerchant = Merchant.get(merchant, raw=['gateway', 'processor_id', 'security_key']);
		if not dMerchant:
			raise Services.EffectException(error=(1400, merchant))

		# Add the gateway to the return
		dRet['merchant'] = dMerchant

		# Look for a customer record in the DB
		dVaultCustomer = VaultCustomer.filter({
			"customer": customer,
			"merchant": merchant
		})

		# If there's one, add it to the return
		if dVaultCustomer:
			dRet['params']['vault_id'] = dVaultCustomer['_id']

		# Else, check we can make a customer
		else:

			# If we have no customer we need certain details
			if 'vault_id' not in dInfo:

				# Verify vault details
				if 'vault' not in data:
					raise Services.EffectException(error=(1001, [('vault', 'missing')]))
				if not VaultValidation.valid(data['vault']):
					raise Services.EffectException(error=(1001, VaultValidation.validation_failures))

				# Add the vault info to the params
				dRet['params'] = data['vault']
				dRet['params']['vault_id'] = VaultCustomer.uuid()
				dRet['oarams']['vault_create'] = True

		# Return what we found
		return dRet

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Payments
		"""
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
				return False
				print("Failed to create `%s` table" % o.tableName())

		# Return OK
		return True

	def authorize_create(self, data):
		"""Authorize

		Transaction authorizations are authorized immediately but are not
		flagged for settlement. These transactions must be flagged for
		settlement using the capture request

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect

		Raises:
			EffectException
		"""

		# Verify data
		if not TransactionValidation.valid(data):
			return Services.Effect(error=(1001, TransactionValidation.validation_failures))

		# Check the customer is in the vault and fetch the gateway
		dInfo = self._checkCustomer(data)

	def capture_create(self, data):
		"""Capture

		Captures flag existing authorizations for settlement. Only
		authorizations can be captured. Captures can be submitted for an amount
		equal to or less than the original authorization

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect

		Raises:
			EffectException
		"""

		# Verify fields
		try: DictHelper.eval(data, ['amount', 'authorize', 'customer', 'merchant'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Check the customer is in the vault and fetch the gateway
		dInfo = self._checkCustomer(data['customer'], d['merchant'])

	def credit_create(self, data):
		"""Credit

		Transaction credits apply an amount to the cardholder's card that was
		not originally processed through the Gateway. In most situations credits
		are disabled as refunds should be used instead

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect

		Raises:
			EffectException
		"""

		# Verify fields
		try: DictHelper.eval(data, ['amount', 'customer', 'merchant'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Check the customer is in the vault and fetch the gateway
		dInfo = self._checkCustomer(data['customer'], data['merchant'])

	def customerCopy_update(self, data):
		"""Customer Copy

		Copies a customer from one mid vault into another mid's vault

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect

		Raises:
			EffectException
		"""
		pass

	def refund_create(self, data):
		"""Refund

		Transaction refunds will reverse a previously settled or pending
		settlement transaction. If the transaction has not been settled, a
		void request can also reverse it

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect

		Raises:
			EffectException
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer', 'merchant', 'transaction'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Check the customer is in the vault and fetch the gateway
		dInfo = self._checkCustomer(data['customer'], data['merchant'])

	def sale_create(self, data):
		"""Sale

		Sales are submitted and immediately flagged for settlement

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect

		Raises:
			EffectException
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer', 'merchant', 'transaction'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Check the customer is in the vault and fetch the gateway
		dInfo = self._checkCustomer(data['customer'], data['merchant'])

	def validate_create(self, data):
		"""Validate

		Used for doing an "Account Verification" on the cardholder's credit card
		without actually doing an authorization

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect

		Raises:
			EffectException
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer', 'merchant'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Check the customer is in the vault and fetch the gateway
		dInfo = self._checkCustomer(data['customer'], data['merchant'])

	def void_create(self, data):
		"""Void

		Voids will cancel an existing sale or captured authorization. In
		addition, non-captured authorizations can be voided to prevent any
		future capture. Voids can only occur if the transaction has not been
		settled

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect

		Raises:
			EffectException
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer', 'merchant'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Check the customer is in the vault and fetch the gateway
		dInfo = self._checkCustomer(data['customer'], data['merchant'])

