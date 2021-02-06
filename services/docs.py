# coding=utf8
""" Docs Service

Handles all Documentation requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2021-02-06"

# Pip imports
from RestOC import Conf, DictHelper, Errors, Record_MySQL, Services

# Shared imports
from shared import Rights

# Records imports
from records.docs import ErrorRecord, NounRecord, ServiceRecord

class Docs(Services.Service):
	"""Docs Service class

	Service for Documentation
	"""

	_install = [ErrorRecord, NounRecord, ServiceRecord]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Auth
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

	def error_create(self, data, sesh):
		"""Error Create

		Create a new Error record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'documentation', Rights.CREATE)

		# Try to create a new instance
		try:
			oError = ErrorRecord(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Try to store the new record
		try:
			sID = oError.create()
		except Record_MySQL.DuplicateException:
			return Services.Error(1101)

		# Return the new ID
		return Services.Response(sID)

	def error_delete(self, data, sesh):
		"""Error Delete

		Deletes an existing new Error record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'documentation', Rights.DELETE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the record
		oError = ErrorRecord.get(data['_id'])
		if not oError:
			return Services.Error(1104)

		# Delete the record and return the result
		return Services.Response(
			oError.delete()
		)

	def error_update(self, data):
		"""Error Update

		Updates an existing Error record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'documentation', Rights.UPDATE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the record
		oError = ErrorRecord.get(data['_id'])
		if not oError:
			return Services.Error(1104)

		# Delete fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if '_updated' in data: del data['_updated']

		# Try to update the remaining fields
		lErrors = []
		for f in data:
			try: oError[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Error(1001, lErrors)

		# Try to store the changes
		try:
			bRes = oError.save()
		except Record_MySQL.DuplicateException:
			return Services.Error(1101)

		# Return the result of the save
		return Services.Response(bRes)

	def errors_read(self, data):
		"""Errors Read

		Returns all Error records

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Fetch and return all errors ordered by code
		return Services.Response(
			ErrorRecord.get(raw=True, orderby='code')
		)

	def noun_create(self, data, sesh):
		"""Noun Create

		Create a new Noun record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'documentation', Rights.CREATE)

		# Try to create a new instance
		try:
			oError = ServiceRecord(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Make sure the service exists
		if not ServiceRecord.exists(data['service']):
			return Services.Error(1001, [['service', 'invalid']])

		# Try to store the new record
		try:
			sID = oError.create()
		except Record_MySQL.DuplicateException:
			return Services.Error(1101)

		# Return the new ID
		return Services.Response(sID)

	def noun_delete(self, data, sesh):
		"""Noun Delete

		Deletes an existing new Noun record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'documentation', Rights.DELETE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the record
		oNoun = NounRecord.get(data['_id'])
		if not oError:
			return Services.Error(1104)

		# Delete the record and return the result
		return Services.Response(
			oNoun.delete()
		)

	def noun_read(self, data):
		"""Noun Read

		Returns a single Noun record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If we got an '_id'
		if '_id' in data:

			# Find the service by primary key
			dNoun = Noun.get(data['_id'], raw=True)

		# Else, if we got a 'uri'
		elif 'uri' in data:

			# Find the service by uri
			dNoun = NounRecord.filter({
				"uri": data['uri']
			}, raw=True, limit=1)

		# Else, invalid request
		else:
			return Nouns.Error(1001, [['_id', 'missing']])

		# If the record doesn't exist
		if not dNoun:
			return Nouns.Error(1104)

		# Return the service
		return Services.Response(dNoun)

	def noun_update(self, data, sesh):
		"""Noun Update

		Updates an existing Noun record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'documentation', Rights.UPDATE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the record
		oNoun = NounRecord.get(data['_id'])
		if not oNoun:
			return Services.Error(1104)

		# Delete fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if '_updated' in data: del data['_updated']

		# Try to update the remaining fields
		lErrors = []
		for f in data:
			try: oNoun[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Error(1001, lErrors)

		# Try to store the changes
		try:
			bRes = oNoun.save()
		except Record_MySQL.DuplicateException:
			return Services.Error(1101)

		# Return the result of the save
		return Services.Response(bRes)

	def service_create(self, data, sesh):
		"""Service Create

		Create a new Service record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'documentation', Rights.CREATE)

		# Try to create a new instance
		try:
			oError = ServiceRecord(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Try to store the new record
		try:
			sID = oError.create()
		except Record_MySQL.DuplicateException:
			return Services.Error(1101)

		# Return the new ID
		return Services.Response(sID)

	def service_delete(self, data, sesh):
		"""Service Delete

		Deletes an existing new Service record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'documentation', Rights.DELETE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the record
		oService = ServiceRecord.get(data['_id'])
		if not oError:
			return Services.Error(1104)

		# Delete the record and return the result
		return Services.Response(
			oService.delete()
		)

	def service_read(self, data):
		"""Service Read

		Returns a single Service record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If we got an '_id'
		if '_id' in data:

			# Find the service by primary key
			dService = Service.get(data['_id'], raw=True)

		# Else, if we got a 'name'
		elif 'name' in data:

			# Find the service by name
			dService = ServiceRecord.filter({
				"name": data['name']
			}, raw=True, limit=1)

		# Else, invalid request
		else:
			return Services.Error(1001, [['_id', 'missing']])

		# If the record doesn't exist
		if not dService:
			return Services.Error(1104)

		# Return the service
		return Services.Response(dService)

	def service_update(self, data, sesh):
		"""Service Update

		Updates an existing Service record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'documentation', Rights.UPDATE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the record
		oService = ServiceRecord.get(data['_id'])
		if not oService:
			return Services.Error(1104)

		# Delete fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if '_updated' in data: del data['_updated']

		# Try to update the remaining fields
		lErrors = []
		for f in data:
			try: oService[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Error(1001, lErrors)

		# Try to store the changes
		try:
			bRes = oService.save()
		except Record_MySQL.DuplicateException:
			return Services.Error(1101)

		# Return the result of the save
		return Services.Response(bRes)

	def services_read(self, data):
		"""Services Read

		Returns all Service records

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Fetch and return all services alphabetically
		return Services.Response(
			ServiceRecord.get(raw=True, orderby='title')
		)
