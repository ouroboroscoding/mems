# coding=utf8
""" Reports Service

Handles all Reports requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-08-18"

# Pip imports
import arrow
from RestOC import Conf, DictHelper, Errors, Record_MySQL, Services

# Shared imports
from shared import Rights

# Records imports
from records.reports import Recipients

class Reports(Services.Service):
	"""Reports Service class

	Service for Reportsorization, sign in, sign up, etc.
	"""

	_install = [Recipients]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Reports
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

	def recipients_create(self, data, sesh):
		"""Recipients Create

		Creates a new list of recipients for a report

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "report_recipients",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['name', 'addresses'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure addresses are a list
		if not isinstance(data['addresses'], list):
			return Services.Response(error=(1001, [('addresses', 'is not a list')]))

		# Try to create an instance to validate the values
		try:
			oRecipients = Recipients({
				"name": data['name'],
				"addresses": ','.join(data['addresses'])
			})
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Try to create the record and return the new ID
		try:
			return Services.Response(
				oRecipients.create()
			)

		# If the name is a duplicate, return an error
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

	def recipients_delete(self, data, sesh):
		"""Recipients Delete

		Deletes an existing list of recipients for a report

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "report_recipients",
			"right": Rights.DELETE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oRecipients.get(data['_id'])
		if not oRecipients:
			return Services.Response(error=1104)

		# Delete the record and return the response
		return Services.Response(
			oRecipients.delete()
		)

	def recipients_read(self, data, sesh):
		"""Recipients Read

		Fetches and returns all recipients for all reports

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "report_recipients",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		for d in Recipients.get(raw=True):
			print(d)

		# Fetch all records and return the id, name, and addresses as a list
		return Services.Response([{
			"_id": d['_id'],
			"name": d['name'],
			"addresses": (d['addresses'] != '' and d['addresses'].split(',') or [])
		} for d in Recipients.get(raw=True, orderby="name")])

	def recipientsInternal_read(self, data, sesh):
		"""Recipients Read

		Fetches and returns a list of recipients for a report

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'name'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Find the record by name
		dRecipients = Recipients.filter({
			"name": data['name']
		}, raw=['addresses'])

		# If it doesn't exist
		if not dRecipients:
			return Services.Response([])

		# Split the value by comma and return
		return Services.Response(
			dRecipients['addresses'].split(',')
		)

	def recipients_update(self, data, sesh):
		"""Recipients Update

		Update an existing list of recipients for a report

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "report_recipients",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oRecipients = Recipients.get(data['_id'])
		if not oRecipients:
			return Services.Response(error=1104)

		# If there's any errors
		lErrors = []

		# If name is passed and changed
		if 'name' in data and data['name'] != oRecipients['name']:

			# Make sure we don't already have it
			if Recipients.filter({"name": data['name']}, raw=['_id']):
				return Services.Response(error=1101)

			# Store the name
			try: oRecipients['name'] = data['name']
			except ValueError as e: lErrors.append(e.args[0])

		# If addresses are passed
		if 'addresses' in data:

			# Make sure addresses are a list
			if not isinstance(data['addresses'], list):
				return Services.Response(error=(1001, [('addresses', 'is not a list')]))

			# Store the addresses
			try: oRecipients['addresses'] = ','.join(data['addresses'])
			except ValueError as e: lErrors.append(e.args[0])

		# If there's any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Store the changes and return the result
		return Services.Response(
			oRecipients.save()
		)
