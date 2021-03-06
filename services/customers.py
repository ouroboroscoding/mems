# coding=utf8
""" Customers Service

Handles all Customers requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-18"

# Pip imports
import arrow
from RestOC import Conf, DictHelper, Errors, Record_MySQL, Services

# Shared imports
from shared import Rights

# Records imports
from records.customers import Address, Customer, Note

class Customers(Services.Service):
	"""Customers Service class

	Service for customer access
	"""

	_install = [Address, Customer, Note]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Customers
		"""

		# Store the config
		self._conf = Conf.get(('services', 'customers'))

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
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers', Rights.UPDATE, data['customer'])

		# Make sure the customer exists
		if not Customer.exists(data['customer']):
			return Services.Response(error=1104)

		# Create a new instance of the Address to verify fields
		try:
			oAddress = Address(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# If the label is too long
		if len(data['label']) > 20:
			return Services.Response(error=(1001, [('label', 'too long')]))

		# Create the record in the DB
		try:
			oAddress.create(changes={"user": sesh['user_id']})

		# If it's a duplicate
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

		# Return the ID of the new address
		return Services.Response(oAddress['_id'])

	def address_read(self, data, sesh):
		"""Address Read

		Fetches and returns a specific address

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the address
		dAddress = Address.get(data['_id'], raw=True)
		if not dAddress:
			return Services.Response(error=1104)

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers', Rights.READ, dAddress['customer'])

		# Return the address record
		return Services.Response(dAddress)

	def address_update(self, data, sesh):
		"""Address Update

		Updates an existing address, or creates a new one from an existing one

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the address
		oAddress = Address.get(data['_id'])
		if not oAddress:
			return Services.Response(error=1104)

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers', Rights.UPDATE, oAddress['customer'])

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if '_updated' in data: del data['_updated']
		if 'customer' in data: del data['customer']

		# Store the current raw record from the address
		dCurrRecord = oAddress.record()

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oAddress[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# If the label is too long
		if 'label' in data and len(data['label']) > 20:
			return Services.Response(error=(1001, [('label', 'too long')]))

		# Are there are no changes in the record
		if not oAddress.changes():
			return Services.Response(False)

		# Will we need to make a new instance instead of updating the existing?
		bNewInstance = False

		# If we didn't find the address in the customer, poll other services
		#	that might be using the address
		for sService in self._conf['address_services']:
			oResponse = Services.read(sService, 'checkAddress', {
				"_internal_": Services.internalKey(),
				"address": oAddress['_id']
			})
			if oResponse.errorExists(): return oResponse
			if oResponse.data:
				bNewInstance = True
				break

		# If we need a new instance
		if bNewInstance:

			# Copy the raw record
			dNewRecord = oAddress.record()

			# Remove fields that will be filled in on create
			for f in ['_id', '_created', '_updated']:
				del dNewRecord['data']

			# Create the new instance and store it in the DB
			oNewAddress = Address(dNewRecord)
			oNewAddress.create(changes={"user": sesh['user_id']})

			# Update the old addresses label and deactivate it
			oOldAddress = Address(dOldRecord)
			oOldAddress['active'] = False
			oOldAddress['label'] = '%s ~%s~' % (
				oOldAddress['label'],
				arrow.get().format('YYYY-MM-DD HH:mm')
			)
			oOldAddress.save(changes={"user": sesh['user_id']})

			# Does the instance exist in either billing or shipping? If it does
			#	update one or both
			oCustomer = Customer.get(oAddress['customer'])
			if oCustomer['billing'] == oAddress['_id']:
				oCustomer['billing'] = oNewAddress['_id']
			if oCustomer['shipping'] == oAddress['_id']:
				oCustomer['shipping'] = oNewAddress['_id']
			oCustomer.save(changes={"user": sesh['user_id']})

			# Return both the new and old Address
			return Services.Response({
				"old": oOldAddress.record(),
				"new": oNewAddress.record()
			})

		# Else, just save the address and return OK
		else:
			oAddress.save(changes={"user": sesh['user_id']})
			return Services.Response(True)

	def customer_create(self, data, sesh):
		"""Customer Create

		Creates a new customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers', Rights.CREATE)

		# At minimum we need an email address
		try: DictHelper.eval(data, ['email'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make email lowercase
		data['email'] = data['email'].lower()

		# Check for a user with the email, if it already exists, don't allow
		#	and return the ID of the found customer
		dCustomer = Customer.filter({"email": data['email']}, raw=['_id'], limit=1)
		if dCustomer:
			return Services.Response(error=(2000, dCustomer['_id']))

		# Create a new instance to validate the data
		try:
			oCustomer = Customer(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the customer in the DB
		try:
			oCustomer.create(changes={"user": sesh['user_id']})
		except Record_MySQL.DuplicateException:
			return Services.Response(error=2000)

		# Return the ID of the new customer
		return Services.Response(oCustomer['_id'])

	def customer_read(self, data, sesh):
		"""Customer Read

		Fetches and returns an existing customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers', Rights.READ, data['_id'])

		# Find the customer
		dCustomer = Customer.get(data['_id'], raw=True)
		if not dCustomer:
			return Services.Response(error=1104)

		# If additional data was requested
		if 'include' in data:

			# If addresses were requested
			if 'addresses' in data['include']:
				dCustomer['addresses'] = Address.filter({
					"customer": data['_id']
				}, raw=True)

			# If notes were requested
			if 'notes' in data['include']:
				dCustomer['notes'] = Note.filter({
					"customer": data['_id']
				}, raw=True)

		# Return the customer
		return Services.Response(dCustomer)

	def customer_update(self, data, sesh):
		"""Customer Update

		Updates an existing customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers', Rights.UPDATE, data['_id'])

		# Fetch the customer
		oCustomer = Customer.get(data['_id'])
		if not oCustomer:
			return Services.Response(error=1104)

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if '_updated' in data: del data['_updated']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oCustomer[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Response(
			oCustomer.save(changes={"user": sesh['user_id']})
		)

	def customerAddresses_read(self, data, sesh):
		"""Customer Addresses

		Returns all addresses associated with a customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers', Rights.READ, data['customer'])

		# If the deactivated flag wasn't passed
		if 'deactivated' not in data:
			data['deactivated'] = False

		# Create the filter
		dFilter = {"customer": data['customer']}

		# If we only want the active
		if not data['deactivated']:
			dFilter['active'] = True

		# Find and return all addresses associated with the given customer
		return Services.Response(
			Address.filter(dFilter, raw=True)
		)

	def customerNotes_read(self, data, sesh):
		"""Customer Notes

		Returns all notes associated with a customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers_notes', Rights.READ, data['customer'])

		# Get all the notes
		lNotes = Note.filter({
			"customer": data['customer']
		}, raw=True)

		# If there's no notes
		if not lNotes:
			return Services.Response([])

		# Get all the user's associated with the notes
		oResponse = Services.read('auth', 'user/names', {
			"_id": [d['user'] for d in lNotes]
		})
		if oResponse.errorExists(): return oResponse
		dUsers = oResponse.data

		# Add the name to each note
		for d in lNotes:
			d['userName'] = d['user'] in dUsers and '%s %s' % (dUsers[d['user']]['firstName'], dUsers[d['user']]['lastName']) or 'N/A'

		# Return all the notes
		return Services.Response(lNotes)

	def note_create(self, data, sesh):
		"""Note Create

		Creates a new note associated with a customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customer'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'customers_notes', Rights.CREATE, data['customer'])

		# Make sure the customer exists
		if not Customer.exists(data['customer']):
			return Services.Response(error=1104)

		# Create a new instance of the Note to verify fields
		try:
			data['user'] = sesh['user_id']
			oNote = Note(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the record in the DB and return the new ID
		return Services.Response(
			oNote.create()
		)

	def search_read(self, data, sesh):
		"""Search

		Search for customers

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['filter'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If the filter isn't a dict
		if not isinstance(data['filter'], dict):
			return Services.Response(error=(1001, [('filter', "must be a key:value store")]))

		# If fields is not a list
		if 'fields' in data and not isinstance(data['fields'], list):
			return Services.Response(error=(1001, [('fields', "must be a list")]))

		# Search based on the data passed
		lRecords = Customer.search(data['filter'], raw=('fields' in data and data['fields'] or True))

		# Return the results
		return Services.Response(lRecords)
