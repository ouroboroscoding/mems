# coding=utf8
""" Qualified Medication Service

Handles all Qualified Medication requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-10-12"

# Pip imports
import arrow
from RestOC import Conf, DictHelper, Errors, Record_MySQL, Services

# Shared imports
from shared import Rights

# Records imports
from records.qualmed import Item

class QualMed(Services.Service):
	"""QualMed Service class

	Service for qualified medication items
	"""

	_install = [Item]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			QualMed
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

	def item_create(self, data, sesh):
		"""Item Create

		Creates a new qualified medication item

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "qualmed",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customer'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Create a new instance to validate the data
		try:
			oItem = Item(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the product in the DB
		try:
			oItem.create(changes={"user": sesh['user_id']})
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

		# Return the ID of the new item
		return Services.Response(oGroup['_id'])

	def item_delete(self, data, sesh):
		"""Item Delete

		Deletes a new product

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Fetch the item
		oItem = Item.get(data['_id'])
		if not oItem:
			return Services.Response(error=1104)

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "qualmed",
			"right": Rights.DELETE,
			"ident": oItem['customer']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Delete the instance and return the result
		return Services.Response(
			oItem.delete()
		)

	def item_read(self, data, sesh):
		"""Item Read

		Fetches and returns an existing item

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Fetch the item
		dItem = Item.get(data['_id'], raw=True)
		if not dItem:
			return Services.Response(error=1104)

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "qualmed",
			"right": Rights.READ,
			"ident": dItem['customer']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Return the raw data
		return Services.Response(dItem)

	def item_update(self, data, sesh):
		"""Item Update

		Updates an existing item

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Fetch the item
		oItem = Item.get(data['_id'])
		if not oItem:
			return Services.Response(error=1104)

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "qualmed",
			"right": Rights.UPDATE,
			"ident": oItem['customer']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if '_updated' in data: del data['_updated']
		if 'customer' in data: del data['customer']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oItem[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Response(
			oItem.save(changes={"user": sesh['user_id']})
		)

	def items_read(self, data, sesh):
		"""Items

		Returns all the qualified medication for a single customer

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
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "qualmed",
			"right": Rights.READ,
			"ident": data['customer']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Return all the items
		return Services.Response(
			Item.filter({"customer": data['customer']}, raw=True)
		)
