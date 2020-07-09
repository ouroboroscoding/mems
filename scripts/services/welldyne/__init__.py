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
		lRecords = AdHoc.get(raw=['id', 'customerId', 'type', 'user', 'ready'])

		# If we have records
		if lRecords:

			# Find all the customer names
			oEff = Services.read('monolith', 'customer/name', {
				"id": [d['customerId'] for d in lRecords]
			}, sesh)
			if oEff.errorExists(): return oEff
			dCustomers = oEff.data

			# Find all the user names
			oEff = Services.read('monolith', 'user/name', {
				"id": [d['user'] for d in lRecords]
			}, sesh)
			if oEff.errorExists(): return oEff
			dUsers = oEff.data
			dUsers[0] = 'WellDyneRX'

			# Go through each record and add the customer and user names
			for d in lRecords:
				d['customerName'] = d['customerId'] in dCustomers and ('%s %s' % (d['firstName'], d['lastName'])) or 'Unknown'
				d['userName'] = d['user'] in dUsers and ('%s %s' % (d['firstName'], d['lastName'])) or 'Unknown'

		# Return all records
		return Services.Effect(lRecords)

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

		# Fetch all the records
		lRecords = Outreach.get(raw=['id', 'customerId', 'queue', 'reason', 'user', 'ready'])

		# If we have records
		if lRecords:

			# Find all the customer names
			oEff = Services.read('monolith', 'customer/name', {
				"id": [str(d['customerId']) for d in lRecords]
			}, sesh)
			if oEff.errorExists(): return oEff
			dCustomers = oEff.data

			# Find all the user names
			oEff = Services.read('monolith', 'user/name', {
				"id": list(set([d['user'] for d in lRecords]))
			}, sesh)
			if oEff.errorExists(): return oEff
			dUsers = oEff.data
			dUsers['0'] = 'WellDyneRX'

			# Go through each record and add the customer and user names
			for d in lRecords:
				sCustId = str(d['customerId'])
				sUserId = str(d['user'])
				d['customerName'] = sCustId in dCustomers and ('%s %s' % (dCustomers[sCustId]['firstName'], dCustomers[sCustId]['lastName'])) or 'Unknown'
				d['userName'] = d['user'] in dUsers and ('%s %s' % (dUsers[d['user']]['firstName'], dUsers[d['user']]['lastName'])) or 'Unknown'

		# Return all records
		return Services.Effect(lRecords)

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
