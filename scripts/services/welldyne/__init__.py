# coding=utf8
""" WellDyne Service

Handles all WellDyneRx requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-07-03"

# Python imports
import re
from time import time
import uuid

# Pip imports
import arrow
from RestOC import Conf, DictHelper, Errors, Services, Sesh

# Shared imports
from shared import Rights

# Service imports
from .records import AdHoc, Eligibility, Outreach, Trigger

class WellDyne(Services.Service):
	"""WellDyne Service class

	Service for WellDyne, sign in, sign up, etc.
	"""

	_install = []
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			WellDyne
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

	def adhoc_create(self, data, sesh):
		"""AdHoc Create

		Adds a new record to the AdHoc report

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_adhoc",
			"right": Rights.CREATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['customerId', 'type'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Check the customer exists
		oEff = Services.read('monolith', 'customer/name', {
			"customerId": str(data['customerId'])
		}, sesh)
		if oEff.errorExists(): return oEff
		dCustomer = oEff.data

		# Get the user name
		oEff = Services.read('monolith', 'user/name', {
			"id": sesh['memo_id']
		}, sesh)
		if oEff.errorExists(): return oEff
		dUser = oEff.data

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Try to create a new instance of the adhoc
		try:
			data['user'] = sesh['memo_id']
			data['createdAt'] = sDT
			data['updatedAt'] = sDT
			oAdHoc = AdHoc(data)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record and return the result
		return Services.Effect({
			"id": oAdHoc.create(),
			"customerName": '%s %s' % (dCustomer['firstName'], dCustomer['lastName']),
			"userName": '%s %s' % (dUser['firstName'], dUser['lastName'])
		})

	def adhoc_delete(self, data, sesh):
		"""AdHoc Delete

		Deletes an existing record from the AdHoc report

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_adhoc",
			"right": Rights.DELETE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oAdHoc = AdHoc.get(data['id'])
		if not oAdHoc:
			return Services.Effect(error=1104)

		# Delete the record and return the result
		return Services.Effect(
			oAdHoc.delete()
		)

	def adhocs_read(self, data, sesh):
		"""Adhocs

		Returns all adhoc records

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_adhoc",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Fetch all the records
		lRecords = AdHoc.get(raw=['id', 'customerId', 'type', 'user'])

		# If we have records
		if lRecords:

			# Find all the customer names
			oEff = Services.read('monolith', 'customer/name', {
				"customerId": [str(d['customerId']) for d in lRecords]
			}, sesh)
			if oEff.errorExists(): return oEff
			dCustomers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oEff.data.items()}

			# Find all the user names
			oEff = Services.read('monolith', 'user/name', {
				"id": list(set([d['user'] for d in lRecords]))
			}, sesh)
			if oEff.errorExists(): return oEff
			dUsers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oEff.data.items()}

			# Go through each record and add the customer and user names
			for d in lRecords:
				sCustId = str(d['customerId'])
				sUserId = str(d['user'])
				d['customerName'] = sCustId in dCustomers and dCustomers[sCustId] or 'Unknown'
				d['userName'] = sUserId in dUsers and dUsers[sUserId] or 'Unknown'

		# Return all records
		return Services.Effect(lRecords)

	def outreach_create(self, data, sesh):
		"""Outreach Create

		Adds a new record to the Outreach report

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_outreach",
			"right": Rights.CREATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Check the customer exists
		oEff = Services.read('monolith', 'customer/name', {
			"customerId": str(data['customerId'])
		}, sesh)
		if oEff.errorExists(): return oEff
		dCustomer = oEff.data

		# Get the user name
		oEff = Services.read('monolith', 'user/name', {
			"id": sesh['memo_id']
		}, sesh)
		if oEff.errorExists(): return oEff
		dUser = oEff.data

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Try to create a new instance of the outreach
		try:
			if 'queue' not in data: data['queue'] = ''
			if 'reason' not in data: data['reason'] = ''
			if 'rx' not in data: data['rx'] = 0
			data['user'] = sesh['memo_id']
			data['createdAt'] = sDT
			data['updatedAt'] = sDT
			oOutreach = Outreach(data)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record and return the result
		return Services.Effect({
			"id": oOutreach.create(),
			"customerName": '%s %s' % (dCustomer['firstName'], dCustomer['lastName']),
			"userName": '%s %s' % (dUser['firstName'], dUser['lastName'])
		})

	def outreach_delete(self, data, sesh):
		"""Outreach Delete

		Deletes an existing record from the Outreach report

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_outreach",
			"right": Rights.DELETE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oOutreach = Outreach.get(data['id'])
		if not oOutreach:
			return Services.Effect(error=1104)

		# Delete the record and return the result
		return Services.Effect(
			oOutreach.delete()
		)

	def outreachAdhoc_update(self, data, sesh):
		"""Outreach AdHoc

		Removes a customer from the outreach and puts them as an adhoc / remove
		error record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper outreach rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_outreach",
			"right": Rights.DELETE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Make sure the user has the proper adhoc rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_adhoc",
			"right": Rights.CREATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oOutreach = Outreach.get(data['id'])
		if not oOutreach:
			return Services.Effect(error=1104)

		# Check the customer exists
		oEff = Services.read('monolith', 'customer/name', {
			"customerId": str(oOutreach['customerId'])
		}, sesh)
		if oEff.errorExists(): return oEff
		dCustomer = oEff.data

		# Get the user name
		oEff = Services.read('monolith', 'user/name', {
			"id": sesh['memo_id']
		}, sesh)
		if oEff.errorExists(): return oEff
		dUser = oEff.data

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Try to create a new adhoc instance
		try:
			oAdHoc = AdHoc({
				"customerId": oOutreach['customerId'],
				"type": "Remove Error",
				"user": sesh['memo_id'],
				"createdAt": sDT,
				"updatedAt": sDT
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the adhoc record
		iID = oAdHoc.create();

		# Delete the outreach record
		oOutreach.delete()

		# Turn the adhoc instance into a dict
		dAdHoc = oAdHoc.record()

		# Add the names
		dAdHoc['customerName'] = "%s %s" % (dCustomer['firstName'], dCustomer['lastName'])
		dAdHoc['userName'] = "%s %s" % (dUser['firstName'], dUser['lastName'])

		# Return the new adhoc data
		return Services.Effect(dAdHoc)

	def outreachReady_update(self, data, sesh):
		"""Outreach Ready

		Updates the ready state of an existing outreach record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_outreach",
			"right": Rights.UPDATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['id', 'ready'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oOutreach = Outreach.get(data['id'])
		if not oOutreach:
			return Services.Effect(error=1104)

		# Update the ready state
		oOutreach['ready'] = data['ready'] and True or False

		# Save and return the result
		return Services.Effect(
			oOutreach.save()
		)

	def outreachs_read(self, data, sesh):
		"""Outreachs

		Returns all outreach records

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_outreach",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Fetch all the records joined with the trigger table
		lRecords = Outreach.withTrigger()

		# If we have records
		if lRecords:

			print(lRecords)

			# Find all the customer names
			oEff = Services.read('monolith', 'customer/name', {
				"customerId": [str(d['customerId']) for d in lRecords]
			}, sesh)
			if oEff.errorExists(): return oEff
			dCustomers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oEff.data.items()}

			# Find all the user names
			oEff = Services.read('monolith', 'user/name', {
				"id": list(set([d['user'] for d in lRecords]))
			}, sesh)
			if oEff.errorExists(): return oEff
			dUsers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oEff.data.items()}
			dUsers['0'] = 'WellDyneRX'

			# Go through each record and add the customer and user names
			for d in lRecords:
				sCustId = str(d['customerId'])
				sUserId = str(d['user'])
				d['customerName'] = sCustId in dCustomers and dCustomers[sCustId] or 'Unknown'
				d['userName'] = sUserId in dUsers and dUsers[sUserId] or 'Unknown'

			# Return all records
			return Services.Effect(lRecords)

		# Else return an empty array
		else:
			return Services.Effect([])

	def triggerInfo_read(self, data, sesh):
		"""Trigger Info

		Returns the last trigger associated with the customer, including any
		possible outreach and eligibility

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		#oEff = Services.read('auth', 'rights/verify', {
		#	"name": "welldyne",
		#	"right": Rights.READ
		#}, sesh)
		#if not oEff.data:
		#	return Services.Effect(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for a trigger with any possible outreach and eligibility
		dTrigger = Trigger.withOutreachEligibility(data['customerId'])

		# If there's nothing
		if not dTrigger:
			dTrigger = 0

		# Return
		return Services.Effect(dTrigger)
