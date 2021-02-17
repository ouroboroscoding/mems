# coding=utf8
""" Providers Service

Handles all Providers requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-10-15"

# Python imports
from datetime import timedelta
from time import time
import uuid

# Pip imports
import arrow
from FormatOC import Node
from RestOC import Conf, DictHelper, Errors, Record_MySQL, Services, Sesh, \
					StrHelper

# Shared imports
from shared import Rights, SMSWorkflow

# Records imports
from records.providers import CalendlySingleUse, ProductToRx, Provider, \
								RoundRobinAgent, Template, Tracking

class Providers(Services.Service):
	"""Providers Service class

	Service for Providers access
	"""

	_install = [CalendlySingleUse, ProductToRx, Provider, RoundRobinAgent, \
				Template, Tracking]
	"""Record types called in install"""

	_seshPre = 'prov:'
	"""Prefix for sessions"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Get providers conf
		self._conf = Conf.get(('services', 'providers'))

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

	def _provider_create(self, data, sesh):
		"""Provider Create

		Creates the actual provider record in the DB as well as necessary
		permissions

		Arguments:
			data (dict): The ID of the user in Memo as well as claim vars
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Create a new provider instance using the memo ID
		try:
			oProvider = Provider(data)
		except ValueError:
			return Services.Response(error=(1001, e.args[0]))

		# Create the provider and store the ID
		try:
			sID = oProvider.create()
		except Record_MySQL.DuplicateException as e:
			return Services.Response(error=1101)

		# Create the default permissions
		oResponse = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": sID,
			"permissions": {
				"calendly": 1,			# Read
				"order_claims": 12,		# Create, Delete
				"prov_templates": 1,	# Read
				"customers": 1,			# Read
				"medications": 1,		# Read
				"memo_mips": 3,			# Read, Update
				"memo_notes": 5,		# Read, Update, Create
				"orders": 3,			# Read, Update
				"prescriptions": 7		# Read, Update, Create
			}
		}, sesh)
		if oResponse.errorExists():
			print(oResponse)
			return Services.Response(sID, warning='Failed to creater permissions for provider')

		# Create the provider and return the ID
		return Services.Response(sID)

	def calendlySingle_create(self, data, sesh):
		"""Calendly Single Create

		Creates a single use key for Calendly appointments

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['uri', 'name', 'email', 'crm_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure crm_id is a string
		data['crm_id'] = str(data['crm_id'])

		# Generate a random key
		data['_key'] = StrHelper.random(6, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')

		# Check for errors in the data
		try:
			oRecord = CalendlySingleUse(data);
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Loop until we find a usable random key
		while True:
			try:
				oRecord.create()
				break
			except Record_MySQL.DuplicateException:
				oRecord['_key'] = StrHelper.random(6, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')

		# Return the key used
		return Services.Response(oRecord['_key'])

	def calendlySingle_delete(self, data):
		"""Calendly Single Delete

		Deletes a single use calendly key

		Arguments:
			data (mixed): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_internal_', '_key'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Look for the key
		oRecord = CalendlySingleUse.get(data['_key'])
		if not oRecord:
			return Services.Error(1104)

		# Delete the record and return the result
		return Services.Response(
			oRecord.delete()
		)

	def calendlySingle_read(self, data):
		"""Calendly Single Read

		Returns Calendly data needed to create an embed, assuming the key exists

		Arguments:
			data (mixed): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_key'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look up the key
		dRecord = CalendlySingleUse.get(data['_key'], raw=['uri', 'name', 'email', 'crm_id'])
		if not dRecord:
			return Services.Error(1104)

		# Return the record
		return Services.Response(dRecord)

	def customerToRx_read(self, data, sesh):
		"""Customer To RX Read

		Returns all productions and their prescriptions for a customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prescriptions', Rights.READ)

		# Verify minimum fields
		try: DictHelper.eval(data, ['customer_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find all the records and return them
		return Services.Response(
			ProductToRx.filter({
				"customer_id": data['customer_id']
			}, raw=['product_id', 'ds_id', 'user_id'])
		)

	def customerToRx_update(self, data, sesh):
		"""Customer To RX Update

		Sets the prescription IDs associated with the products the customer
		has

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prescriptions', Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['customer_id', 'products'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Possible errors
		lErrors = []

		# Make sure the customer ID is an int
		try: data['customer_id'] = int(data['customer_id'])
		except ValueError as e: lErrors.append(('customer_id', 'not an int'))

		# If the products are not a list
		if not isinstance(data['products'], list):
			lErrors.append(('products', 'not a list'))
		else:

			# Go through each one and make sure the keys are available, valid, and
			#	not duplicates
			lDsIds = []
			for i in range(len(data['products'])):

				# Set the approved flag
				data['products'][i]['approved'] = True

				# Make sure keys exist
				try: DictHelper.eval(data['products'][i], ['product_id', 'ds_id'])
				except ValueError as e: lErrors.extend([('%d.%s' % (i, f), 'missing') for f in e.args])

				# Make sure the product ID is an int
				try: data['products'][i]['product_id'] = int(data['products'][i]['product_id'])
				except ValueError as e: lErrors.append(('%d.product_id' % i, 'not an int'))

				# Make sure the dosespot ID is an int
				try: data['products'][i]['ds_id'] = int(data['products'][i]['ds_id'])
				except ValueError as e: lErrors.append(('%d.ds_id' % i, 'not an int'))

				# Make sure we don't have the prescription already
				if data['products'][i]['ds_id'] in lDsIds:
					return Services.Response(error=(1101, data['products'][i]['ds_id']))

				# Add the prescription to the list
				lDsIds.append(data['products'][i]['ds_id'])

		# If we have any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Try to create the records
		try:
			ProductToRx.updateCustomer(data['customer_id'], data['products'], sesh['memo_id'])
		except Record_MySQL.DuplicateException as e:
			return Services.Response(error=1101)

		# Return OK
		return Services.Response(True)

	def hours_read(self, data, sesh):
		"""Hours

		Returns breakdown of hours worked by provider

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prov_stats', Rights.READ)

		# Verify minimum fields
		try: DictHelper.eval(data, ['start', 'end',])
		except ValueError as e: return Services.Error(1001, [(f, 'missing') for f in e.args])

		# Fetch all records in the given time period
		lTracking = Tracking.range(data['start'], data['end'])

		# If we got nothing
		if not lTracking:
			return Services.Response([])

		# Init the dictionary of providers
		dProviders = {}

		# Go through each record
		for d in lTracking:

			# If we don't have the provider yet
			if d['memo_id'] not in dProviders:
				dProviders[d['memo_id']] = {
					"seconds": 0,
					"approvals": 0,
					"declines": 0
				}

			# If the action is signin
			if d['action'] == 'signin':
				print('%d - %d = %d' % (d['resolution_ts'], d['action_ts'], (d['resolution_ts'] - d['action_ts'])))
				dProviders[d['memo_id']]['seconds'] += (d['resolution_ts'] - d['action_ts'])

			# Else, if the action is viewed
			elif d['action'] == 'viewed':
				if d['resolution'] == 'approved':
					dProviders[d['memo_id']]['approvals'] += 1
				elif d['resolution'] == 'declined':
					dProviders[d['memo_id']]['declines'] += 1

		# Get the provider names for all the IDs
		oResponse = Services.read('monolith', 'users', {
			"_internal_": Services.internalKey(),
			"id": list(dProviders.keys()),
			"fields": ['id', 'firstName', 'lastName']
		}, sesh)

		# If there's none
		if not oResponse.data:
			dUsers = {}

		# Else, turn it into a dictionary
		else:
			dUsers = {
				d['id']: {'firstName': d['firstName'], 'lastName': d['lastName']}
				for d in oResponse.data
			}

		# Init the return value
		lRet = []

		# Generate the final stats
		for iID in dProviders:

			# Calculate hours
			iHours, iRemainder = divmod(dProviders[iID]['seconds'], 3600)
			iMinutes, iSeconds = divmod(iRemainder, 60)
			sHours = '{:0}:{:02}:{:02}'.format(iHours, iMinutes, iSeconds)

			# Add new row
			lRet.append({
				"memoId": iID,
				"firstName": iID in dUsers and dUsers[iID]['firstName'] or '',
				"lastName": iID in dUsers and dUsers[iID]['lastName'] or '',
				"hours": sHours,
				"approvals": dProviders[iID]['approvals'],
				"declines": dProviders[iID]['declines']
			})

		# Return the list sorted by last name
		return Services.Response(
			sorted(lRet, key=lambda d: d['lastName'])
		)

	def prescriptions_create(self, data, sesh):
		"""Prescriptions Create

		Sends the prescription requests to the prescription service, then stores
		the IDs to the asociated order items as un-approved

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['clinician_id', 'customer_id', 'patient_id', 'products',])
		except ValueError as e: return Services.Error(1001, [(f, 'missing') for f in e.args])

		# Possible errors
		lErrors = []

		# Make sure the fields are all ints
		for f in ['clinician_id', 'customer_id', 'patient_id']:
			try: data[f] = int(data[f])
			except ValueError as e: lErrors.append((f, 'not an int'))

		# If the products are not a list
		if not isinstance(data['products'], list):
			lErrors.append(('products', 'not a list'))
		else:

			# Go through each one and make sure the keys are available, valid,
			#	and not duplicates
			for i in range(len(data['products'])):

				# Make sure keys exist
				try: DictHelper.eval(data['products'][i], ['item_id', 'product_id', 'refills'])
				except ValueError as e: lErrors.extend([('%d.%s' % (i, f), 'missing') for f in e.args])

				# Make sure the values are all ints
				for f in ['item_id', 'refills']:
					try: data['products'][i][f] = int(data['products'][i][f])
					except ValueError as e: lErrors.append(('%d.%s' % (i, f), 'not an int'))

		# If we have any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Go through each product
		lProductToRX = []
		for o in data['products']:

			# Send the request to generate a prescription from the product
			oResponse = Services.create('prescriptions', 'patient/prescription', {
				"clinician_id": data['clinician_id'],
				"effective": o['effective'],
				"patient_id": data['patient_id'],
				"product_id": o['product_id'],
				"refills": o['refills']
			}, sesh)
			if oResponse.errorExists():
				return oResponse

			# Add a new dict to the list of products to RXs
			lProductToRX.append({
				"product_id": o['item_id'],
				"ds_id": oResponse.data,
				"approved": False
			})

		# Try to create the new product to RX records
		try:
			ProductToRx.updateCustomer(data['customer_id'], lProductToRX, sesh['memo_id'])
		except Record_MySQL.DuplicateException as e:
			return Services.Response(error=1101)

		# Return OK
		return Services.Response(True)

	def productToRx_create(self, data, sesh):
		"""Product To RX

		Creates a new record of an unnaproved prescription

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prescriptions', Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['customer_id', 'product_id', 'ds_id',])
		except ValueError as e: return Services.Error(1001, [(f, 'missing') for f in e.args])

		# Make sure the IDs are ints
		lErrors = []
		for k in ['customer_id', 'product_id', 'ds_id']:
			try: data[k] = int(data[k])
			except ValueError as e: lErrors.append((k, 'invalid'))
		if lErrors:
			return Services.Error(1001, lErrors)

		# If approved not sent, assume false
		if 'approved' not in data:
			data['approved'] = False

		# Try to create the records
		try:
			lProducts = [{
				"product_id": data['product_id'],
				"ds_id": data['ds_id'],
				"approved": data['approved']
			}]
			ProductToRx.updateCustomer(data['customer_id'], lProducts, sesh['memo_id'])
		except Record_MySQL.DuplicateException as e:
			return Services.Response(error=1101)

		# Return OK
		return Services.Response(True)

	def provider_create(self, data, sesh):
		"""Provider Create

		Creates a user record associated with the memo user in order to apply
		permissions to it

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'providers', Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['userName', 'firstName', 'lastName', 'password'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Pull out Providers only values
		dProvider = {}
		if 'claims_max' in data: dProvider['claims_max'] = data.pop('claims_max')
		if 'claims_timeout' in data: dProvider['claims_timeout'] = data.pop('claims_timeout')
		if 'agent' in data: dProvider['agent'] = data.pop('agent')

		# Send the data to monolith to create the memo user
		data['_internal_'] = Services.internalKey()
		data['userRole'] = 'Doctor'
		oResponse = Services.create('monolith', 'user', data, sesh)
		if oResponse.errorExists(): return oResponse

		# Add the memo ID
		dProvider['memo_id'] = oResponse.data

		# Create the provider record
		return self._provider_create(dProvider, sesh)

	def provider_delete(self, data, sesh):
		"""Provider Delete

		Deletes an existing memo user record associated

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'providers', Rights.DELETE)

		# Find the Provider
		oProvider = Provider.get(data['_id'])

		# Use the memo ID to mark the memo user as inactive
		oResponse = Services.update('monolith', 'user/active', {
			"_internal_": Services.internalKey(),
			"id": oProvider['memo_id'],
			"active": False
		}, sesh)
		if oResponse.errorExists(): return oResponse

		# Delete all permissions
		oResponse = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": data['_id'],
			"permissions": {}
		}, sesh);
		if oResponse.errorExists(): return oResponse

		# Delete the record and return the result
		return Services.Response(
			oProvider.delete()
		)

	def provider_read(self, data, sesh):
		"""Provider Read

		Fetches one, many, or all user records

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		pass

	def provider_update(self, data, sesh):
		"""Provider Update

		Updates an existing provider (via memo user)

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'providers', Rights.UPDATE)

		# Find the provider
		oProvider = Provider.get(data['_id'])
		if not oProvider:
			return Services.Response(error=1104)

		# Try to update the claims vars
		lErrors = []
		for s in ['claims_max', 'claims_timeout', 'agent']:
			if s in data:
				try: oProvider[s] = data.pop(s)
				except ValueError as e: lErrors.append(e.args[0])
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# If there's any changes
		if oProvider.changes():
			oProvider.save()

		# Remove the provider ID
		del data['_id']

		# If there's still stuff to change
		if data:

			# Add the memo ID
			data['id'] = oProvider['memo_id']

			# Pass the info on to monolith service
			data['_internal_'] = Services.internalKey()
			oResponse = Services.update('monolith', 'user', data, sesh)

			# Return whatever monolith returned
			return oResponse

		# Else, return OK
		else:
			return Services.Response(True)

	def providerInternal_read(self, data, sesh):
		"""Provider Internal

		Fetches a memo user by their Memo ID rather then their primary key.
		Internal function, can not be used from outside

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_internal_', 'id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Look up the record
		dProvider = Provider.filter(
			{"memo_id": data['id']},
			raw=True,
			limit=1
		)

		# If there's no such user
		if not dProvider:
			return Services.Response(error=1104)

		# Return the user
		return Services.Response(dProvider)

	def providerPasswd_update(self, data, sesh):
		"""Provider Password Update

		Updates an provider's password in monolith

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['provider_id', 'passwd'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'providers', Rights.UPDATE, data['provider_id'])

		# Find the Provider
		dProvider = Provider.get(data['provider_id'], raw=['memo_id'])
		if not dProvider:
			return Services.Response(error=1104)

		# Send the data to monolith to update the password
		oResponse = Services.update('monolith', 'user/passwd', {
			"_internal_": Services.internalKey(),
			"user_id": dProvider['memo_id'],
			"passwd": data['passwd']
		}, sesh)

		# Return the result, regardless of what it is
		return oResponse

	def providerPermissions_read(self, data, sesh):
		"""Provider Permissions Read

		Returns all permissions associated with an provider

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['provider_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'providers', Rights.READ, data['provider_id'])

		# Fetch the permissions from the auth service
		oResponse = Services.read('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": data['provider_id']
		}, sesh)

		# Return whatever was found
		return oResponse

	def providerPermissions_update(self, data, sesh):
		"""Provider Permissions Update

		Updates the permissions associated with an provider

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['provider_id', 'permissions'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'providers', Rights.READ, data['provider_id'])

		# Fetch the permissions from the auth service
		oResponse = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": data['provider_id'],
			"permissions": data['permissions']
		}, sesh)

		# Return whatever was found
		return oResponse

	def providerMemo_create(self, data, sesh):
		"""Provider from Memo

		Creates an provider record from an existing Memo user instead of
		creating a new one

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'providers', Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['userName'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the user
		oResponse = Services.read('monolith', 'user/id', {
			"_internal_": Services.internalKey(),
			"userName": data['userName']
		})
		if oResponse.errorExists() or oResponse.data is False:
			return oResponse

		# Create the agent and return the response
		return self._provider_create({
			"memo_id": oResponse.data,
			"claims_max": 20,
			"claims_timeout": 48
		}, sesh)

	def providerTracking_read(self, data, sesh):
		"""Provider Tracking

		Returns all tracking records related to a specfic provider in the given
		timeframe

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prov_stats', Rights.READ)

		# Verify minimum fields
		try: DictHelper.eval(data, ['start', 'end', 'memo_id'])
		except ValueError as e: return Services.Error(1001, [(f, 'missing') for f in e.args])

		# Fetch all records in the given time period
		lTracking = Tracking.range(data['start'], data['end'], data['memo_id'])

		# Go through each record found
		for d in lTracking:

			# Calculate the hours, minutes, and seconds
			iHours, iRemainder = divmod(d['resolution_ts'] - d['action_ts'], 3600)
			iMinutes, iSeconds = divmod(iRemainder, 60)

			# Add the time to the record
			d['time'] = '{:0}:{:02}:{:02}'.format(iHours, iMinutes, iSeconds)

		# Return the records
		return Services.Response(lTracking)

	def providerNames_read(self, data, sesh):
		"""Provider Names

		Returns the list of providers who can have issues transfered / escalated to
		them

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Fetch all the providers
		lProviders = Provider.get(raw=['memo_id'])

		# Fetch their names
		oResponse = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": [d['memo_id'] for d in lProviders]
		}, sesh)

		# Regardless of what we got, retun the effect
		return oResponse

	def providers_read(self, data, sesh):
		"""Providers

		Returns all providers in the system

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'providers', Rights.READ)

		# Fetch all the providers
		lProviders = Provider.get(raw=True)

		# If there's no agents
		if not lProviders:
			return Services.Response([])

		# Memo user fields
		lFields = ['id', 'userName', 'firstName', 'lastName', 'email',
					'cellNumber', 'notificationPref', 'eDFlag', 'hormoneFlag',
					'hairLossFlag', 'urgentCareFlag', 'practiceStates',
					'hrtPracticeStates', 'providerScheduleLink', 'calendlyEmail',
					'dsClinicId', 'dsClinicianId']

		# Fetch all the Memo user's associated
		oResponse = Services.read('monolith', 'users', {
			"_internal_": Services.internalKey(),
			"id": [d['memo_id'] for d in lProviders],
			"fields": lFields
		}, sesh)
		if oResponse.errorExists(): return oResponse

		# Turn it into a dictionary
		dMemoUsers = {d['id']:d for d in oResponse.data}

		# Go through each user and find the memo user
		for d in lProviders:
			if d['memo_id'] in dMemoUsers:
				for f in lFields:
					d[f] = dMemoUsers[d['memo_id']][f]
			else:
				for f in lFields:
					d[f] = None

		# Return the providers in order of userName
		return Services.Response(sorted(lProviders, key=lambda o: o['userName']))

	def roundrobin_read(self, data, sesh):
		"""Round Robin

		Returns all the agent IDs in the round robin table

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return Services.Response([
			d['agent'] for d in RoundRobinAgent.get(raw=True)
		])

	def session_read(self, data, sesh):
		"""Session

		Returns the ID of the user logged into the current session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If the session doesn't start with the proper prefix it's not valid
		if sesh.id()[0:5] != self._seshPre:
			return Services.Response(error=102)

		# Return the session info
		return Services.Response({
			"memo": {"id": sesh['memo_id']},
			"user" : {
				"agent": sesh['agent'],
				"id": sesh['user_id']
			}
		})

	def signin_create(self, data):
		"""Signin

		Signs a user into the system

		Arguments:
			data (dict): The data passed to the request

		Returns:
			Result
		"""

		# Verify fields
		try: DictHelper.eval(data, ['userName', 'passwd'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Check internal key
		data['_internal_'] = Services.internalKey()
		oResponse = Services.create('monolith', 'signin', data)
		if oResponse.errorExists(): return oResponse

		# Generate a new UUID
		sUUID = str(uuid.uuid4())

		# Create a new session using the UUID with a custom TTL
		oSesh = Sesh.create("%s%s" % (self._seshPre, sUUID), self._conf['sesh_ttl'])

		# Store the user ID and information in it
		oSesh['memo_id'] = oResponse.data['id']
		oSesh['states'] = {
			"ed": oResponse.data['eDFlag'] == 'Y' \
					and (oResponse.data['practiceStates'] and oResponse.data['practiceStates'].split(', ')) \
					or None,
			"hrt": oResponse.data['hormoneFlag'] == 'Y' \
					and (oResponse.data['hrtPracticeStates'] and oResponse.data['hrtPracticeStates'].split(', ')) \
					or None
		}

		# Save the session
		oSesh.save()

		# Check for the agent associated with the memo ID
		dProvider = Provider.filter(
			{"memo_id": oResponse.data['id']},
			raw=True,
			limit=1
		)

		# If there's no such user
		if not dProvider:
			return Services.Response(error=Rights.INVALID)

		# Store the user ID and claim vars in the session
		oSesh['agent'] = dProvider['agent']
		oSesh['user_id'] = dProvider['_id']
		oSesh['claims_max'] = dProvider['claims_max']
		oSesh['claims_timeout'] = dProvider['claims_timeout']
		oSesh.save()

		# Look for a pre-existing signin with no sign out
		oPrevTrack = Tracking.filter({
			"memo_id": oSesh['memo_id'],
			"action": 'signin',
			"resolution": None
		}, limit=1, orderby=[['_updated', 'DESC']])
		if oPrevTrack:

			# Look for the oldest viewed in the same session
			dViewed = Tracking.filter({
				"memo_id": oPrevTrack['memo_id'],
				"action": 'viewed',
				"resolution_sesh": oPrevTrack['action_sesh']
			}, orderby=[['resolution_ts', 'DESC']], limit=1)

			# If there's none
			if not dViewed:

				# Delete the previous signin
				oPrevTrack.delete()

			# Else, if there's one
			else:

				# Set the end time to the last viewed's end time
				oPrevTrack['resolution'] = 'new_signin'
				oPrevTrack['resolution_sesh'] = sUUID
				oPrevTrack['resolution_ts'] = dViewed['resolution_ts']
				oPrevTrack.save()

		# Create the sign in tracking
		oTracking = Tracking({
			"memo_id": oSesh['memo_id'],
			"action": 'signin',
			"action_sesh": sUUID,
			"action_ts": int(time())
		})
		oTracking.create()

		# Return the session ID and primary user data
		return Services.Response({
			"memo": {"id": oSesh['memo_id']},
			"session": oSesh.id(),
			"user": {
				"agent": dProvider['agent'],
				"id": dProvider['_id']
			}
		})

	def signout_create(self, data, sesh):
		"""Signout

		Called to sign out a user and destroy their session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Get the current session ID
		sSeshID	= sesh.id()

		# If it starts with the proper prefix
		if sSeshID[0:5] == self._seshPre:

			# Trim the session ID
			sSeshID = sSeshID[5:]

			# Find the previous sign in
			oTracking = Tracking.filter({
				"memo_id": sesh['memo_id'],
				"action": 'signin',
				"action_sesh": sSeshID,
				"resolution" : None
			}, limit=1)

			# If we found one
			if oTracking:

				# Get the current timestamp
				iTS = int(time())

				# If it was a timeout
				if 'timeout' in data and data['timeout']:
					try:
						data['timeout'] = int(data['timeout'])
						iTS -= data['timeout']
					except ValueError:
						return Services.Error(1001, [('timeout', 'not an integer')])

				# End it
				oTracking['resolution'] = 'signout'
				oTracking['resolution_sesh'] = sSeshID
				oTracking['resolution_ts'] = iTS
				oTracking.save()

		# Close the session so it can no longer be found/used
		sesh.close()

		# Return OK
		return Services.Response(True)

	def template_create(self, data, sesh):
		"""Template Email Create

		Create a new email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prov_templates', Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['title', 'type', 'content'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Validate by creating a Record instance
		try:
			oTemplate = Template(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the row and return the result
		return Services.Response(
			oTemplate.create()
		)

	def template_delete(self, data, sesh):
		"""Template Email Delete

		Delete an existing email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prov_templates', Rights.DELETE, data['_id'])

		# If the record does not exist
		if not Template.exists(data['_id']):
			return Services.Response(error=1104)

		# Delete the record
		if not Template.deleteGet(data['_id']):
			return Services.Response(error=1102)

		# Return OK
		return Services.Response(True)

	def template_read(self, data, sesh):
		"""Template Email Read

		Fetches an existing email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prov_templates', Rights.READ, data['_id'])

		# Look for the template
		dTemplate = Template.get(data['_id'], raw=True)

		# If it doesn't exist
		if not dTemplate:
			return Services.Response(error=1104)

		# Return the template
		return Services.Response(dTemplate)

	def template_update(self, data, sesh):
		"""Template Email Update

		Updated an existing email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prov_templates', Rights.UPDATE, data['_id'])

		# Fetch the template
		oTemplate = Template.get(data['_id'])

		# If it doesn't exist
		if not oTemplate:
			return Services.Response(error=1104)

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oTemplate[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Response(
			oTemplate.save()
		)

	def templates_read(self, data, sesh):
		"""Template Emails

		Fetches all existing email templates

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'prov_templates', Rights.READ)

		# Fetch and return the templates
		return Services.Response(
			Template.get(raw=True, orderby=['title'])
		)

	def tracking_create(self, data, sesh):
		"""Tracking

		Internal only request to add tracking to a provider

		Arguments:
			data (mixed): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'crm_type', 'crm_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))
		if 'action' not in data and 'resolution' not in data:
			return Services.Response(error=(1001, [('action', 'missing')]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# If we're creating a new action
		if 'action' in data:

			# If it's not a viewed
			if data['action'] != 'viewed':
				return Services.Response(error=(1001, [('action', 'invalid')]))

			# Create a new tracking instance
			oTracking = Tracking({
				"memo_id": sesh['memo_id'],
				"action": data['action'],
				"action_sesh": sesh.id()[5:],
				"action_ts": int(time()),
				"crm_type": data['crm_type'],
				"crm_id": str(data['crm_id'])
			})
			oTracking.create()

			# Return OK
			return Services.Response(True)

		# Else, we're adding a resolution
		else:

			# If it's not a viewed
			if data['resolution'] not in ['approved', 'declined', 'transferred', 'x']:
				return Services.Response(error=(1001, [('resolution', 'invalid')]))

			# Look for an existing viewed tracking
			oTracking = Tracking.filter({
				"memo_id": sesh['memo_id'],
				"action": "viewed",
				"resolution": None,
				"crm_type": data['crm_type'],
				"crm_id": str(data['crm_id'])
			}, limit=1, orderby=[['_created', 'DESC']])

			# If we found one
			if oTracking:
				oTracking['resolution'] = data['resolution']
				oTracking['resolution_sesh'] = sesh.id()[5:]
				oTracking['resolution_ts'] = int(time())
				oTracking.save()

			# Return
			return Services.Response(oTracking and True or False)
