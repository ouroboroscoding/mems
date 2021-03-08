# coding=utf8
""" Products Service

Handles all Products requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-10-06"

# Pip imports
import arrow
from RestOC import Conf, DictHelper, Errors, Record_MySQL, Services

# Shared imports
from shared import Rights

# Records imports
from records.products import Group, Medication, Product

class Products(Services.Service):
	"""Products Service class

	Service for product groups and medications
	"""

	_install = [Group, Medication, Product]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Products
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

	def group_create(self, data, sesh):
		"""Group Create

		Creates a new product

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Create a new instance to validate the data
		try:
			oGroup = Group(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the product in the DB
		try:
			oGroup.create(changes={"user": sesh['user_id']})
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

		# Return the ID of the new group
		return Services.Response(oGroup['_id'])

	def group_update(self, data, sesh):
		"""Group Update

		Updates an existing group

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
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.UPDATE,
			"ident": data['_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch the group
		oGroup = Group.get(data['_id'])
		if not oGroup:
			return Services.Response(error=1104)

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if '_updated' in data: del data['_updated']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oGroup[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Response(
			oGroup.save(changes={"user": sesh['user_id']})
		)

	def groups_read(self, data, sesh):
		"""Groups

		Returns all Groups in the system

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Return all the groups
		return Services.Response(
			Group.get(orderby='name', raw=True)
		)

	def medication_create(self, data, sesh):
		"""Medication Create

		Creates a new product

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Create a new instance to validate the data
		try:
			oMedication = Medication(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the product in the DB
		try:
			oMedication.create(changes={"user": sesh['user_id']})
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

		# Return the ID of the new medication
		return Services.Response(oMedication['_id'])

	def medication_update(self, data, sesh):
		"""Medication Update

		Updates an existing medication

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
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.UPDATE,
			"ident": data['_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch the medication
		oMedication = Medication.get(data['_id'])
		if not oMedication:
			return Services.Response(error=1104)

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if '_updated' in data: del data['_updated']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oMedication[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Response(
			oMedication.save(changes={"user": sesh['user_id']})
		)

	def medications_read(self, data, sesh):
		"""Medications

		Returns all Medications in the system

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Return all the groups
		return Services.Response(
			Medication.get(orderby=['name'], raw=True)
		)

	def product_create(self, data, sesh):
		"""Product Create

		Creates a new product

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Create a new instance to validate the data
		try:
			oProduct = Product(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the product in the DB
		try:
			oProduct.create(changes={"user": sesh['user_id']})
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

		# Return the ID of the new product
		return Services.Response(oProduct['_id'])

	def product_read(self, data, sesh):
		"""Product Read

		Fetches and returns an existing product

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
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.READ,
			"ident": data['_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Find the product
		dProduct = Product.get(data['_id'], raw=True)
		if not dProduct:
			return Services.Response(error=1104)

		# Return the product
		return Services.Response(dProduct)

	def product_update(self, data, sesh):
		"""Product Update

		Updates an existing product

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
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.UPDATE,
			"ident": data['_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch the product
		oProduct = Product.get(data['_id'])
		if not oProduct:
			return Services.Response(error=1104)

		# If the name is set and different
		if 'name' in data and data['name'] != oProduct['name']:

			# Check for a product with the name, if it already exists, don't
			#	allow and return the ID of the found product
			dProduct = Product.filter({"name": data['name']}, raw=['_id'], limit=1)
			if dProduct:
				return Services.Response(error=(1101, dProduct['_id']))

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if '_updated' in data: del data['_updated']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oProduct[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Response(
			oProduct.save(changes={"user": sesh['user_id']})
		)

	def products_read(self, data, sesh):
		"""Products

		Returns all products sorted by group and then name

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "products",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Return all the groups
		return Services.Response(
			Product.allByGroup()
		)
