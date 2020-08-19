# coding=utf8
""" Customers Service

Handles all Customers requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-10-18"

# Pip imports
from RestOC import Conf, DictHelper, Errors, Services

# Shared imports
from shared import Rights

# Records imports
from records.auth import Address, Customer, Note

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

class Customers(Services.Service):
	"""Customers Service class

	Service for Customersorization, sign in, sign up, etc.
	"""

	_install = [Address, Customer, Note]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Customers
		"""

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

	def address_create(self, data, sesh):
		"""Address Create

		Creates a new address associated with a specific customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.UPDATE,
			"ident": data['customer']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

	def address_read(self, data, sesh):
		"""Address Read

		Fetches and returns a specific address

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the address
		oAddress = Address.get(data['_id'])
		if not oAddress:
			return Services.Effect(error=1104)

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.READ,
			"ident": oAddress['customer']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Return the raw record
		return Services.Effect(
			oAddress.record()
		)

	def address_update(self, data, sesh):
		"""Address Update

		Updates an existing address, or creates a new one from an existing one

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the address
		oAddress = Address.get(data['_id'])
		if not oAddress:
			return Services.Effect(error=1104)

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.UPDATE,
			"ident": oAddress['customer']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

	def customer_create(self, data, sesh):
		"""Customer Create

		Creates a new customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.CREATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# At minimum we need an email address
		try: DictHelper.eval(data, ['email'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make email lowercase
		data['email'] = data['email'].lower()

		# Check for a user with the email
		dCustomer = Customer.filter({"email": data['email']}, raw=['_id'])

		# Customer already exists, return an error with the ID found
		if dCustomer:
			return Services.Effect(error=(2000, dCustomer['_id']))

		# Create a new instance to validate the data
		try:
			oCustomer = Customer(data)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the customer in the DB
		try:
			oCustomer.create()
		except Record_MySQL.DuplicateException:
			return Services.Effect(error=2000)

	def customer_read(self, data, sesh):
		"""Customer Read

		Fetches and returns an existing customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.READ,
			"ident": data['_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

	def customer_update(self, data, sesh):
		"""Customer Update

		Updates an existing customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.UPDATE,
			"ident": data['_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

	def customerAddresses_read(self, data, sesh):
		"""Customer Addresses

		Returns all addresses associated with a customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.READ,
			"ident": data['customer']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

	def customerNotes_read(self, data, sesh):
		"""Customer Notes

		Returns all notes associated with a customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.READ,
			"ident": data['customer']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)


	def note_create(self, data, sesh):
		"""Note Create

		Creates a new note associated with a customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.UPDATE,
			"ident": data['customer']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		pass
