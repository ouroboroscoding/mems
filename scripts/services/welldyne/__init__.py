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

		# Check the customer exists
		oEff = Services.read('monolith', 'customer/exists', {
			"customerId": str(data['customerId'])
		}, sesh)
		if oEff.errorExists(): return oEff

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Try to create a new instance of the adhoc
		try:
			oAdHoc = AdHoc({
				"customerId": data['customerId'],
				"type": data['type'],
				"user": sesh['memo_id'],
				"createdAt": sDT,
				"updatedAt": sDT
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record and return the result
		return Services.Effect(
			oAdHoc.create()
		)

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
