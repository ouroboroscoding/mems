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

# Pip imports
from RestOC import DictHelper, Services

# Shared imports
from shared import Rights

# Service imports
from records.welldyne import \
	AdHoc, AdHocSent, Eligibility, Outbound, OutboundSent, \
	RxNumber, Trigger

class WellDyne(Services.Service):
	"""WellDyne Service class

	Service for WellDyne, sign in, sign up, etc.
	"""

	_install = [AdHoc, AdHocSent, Outbound, OutboundSent, RxNumber, Trigger]
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
		"""OldAdHoc Create

		Adds a new record to the OldAdHoc report

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
		try: DictHelper.eval(data, ['crm_id', 'type'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# If the type isn't set
		if 'crm_type' not in data:
			data['crm_type'] = 'knk'

		# If the CRM is Konnektive
		if data['crm_type'] == 'knk':

			# Check the customer exists
			oEff = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": data['crm_id']
			}, sesh)
			if oEff.errorExists(): return oEff
			dCustomer = oEff.data

		# Else, invalid CRM
		else:
			return Services.Effect(error=1003)

		# Get the user name
		oEff = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": sesh['memo_id']
		}, sesh)
		if oEff.errorExists(): return oEff
		dUser = oEff.data

		# Try to create a new instance of the adhoc
		try:
			data['memo_user'] = sesh['memo_id']
			oAdHoc = AdHoc(data)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record and return the result
		return Services.Effect({
			"_id": oAdHoc.create(),
			"customer_name": '%s %s' % (dCustomer['firstName'], dCustomer['lastName']),
			"user_name": '%s %s' % (dUser['firstName'], dUser['lastName'])
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
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oAdHoc = AdHoc.get(data['_id'])
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
		lRecords = AdHoc.get(raw=True)

		# If we have records
		if lRecords:

			# Find all the customer names
			oEff = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": [d['crm_id'] for d in lRecords]
			}, sesh)
			if oEff.errorExists(): return oEff
			dCustomers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oEff.data.items()}

			# Find all the user names
			oEff = Services.read('monolith', 'user/name', {
				"_internal_": Services.internalKey(),
				"id": list(set([d['memo_user'] for d in lRecords]))
			}, sesh)
			if oEff.errorExists(): return oEff
			dUsers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oEff.data.items()}

			# Go through each record and add the customer names
			for d in lRecords:
				d['customer_name'] = d['crm_id'] in dCustomers and dCustomers[d['crm_id']] or 'Unknown'
				sUserId = str(d['memo_user'])
				d['user_name'] = sUserId in dUsers and dUsers[sUserId] or 'Unknown'

		# Return all records
		return Services.Effect(lRecords)

	def outboundAdhoc_update(self, data, sesh):
		"""Outbound OldAdHoc

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
			"name": "welldyne_outbound",
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
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oOutbound = Outbound.get(data['_id'])
		if not oOutbound:
			return Services.Effect(error=1104)

		# If the CRM is Konnektive
		if oOutbound['crm_type'] == 'knk':

			# Check the customer exists
			oEff = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": oOutbound['crm_id']
			}, sesh)
			if oEff.errorExists(): return oEff
			dCustomer = oEff.data

		# Else, invalid CRM type
		else:
			return Services.Effect(error=1003)

		# Get the user name
		oEff = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": sesh['memo_id']
		}, sesh)
		if oEff.errorExists(): return oEff
		dUser = oEff.data

		# Try to create a new adhoc instance
		try:
			oAdHoc = AdHoc({
				"crm_type": oOutbound['crm_type'],
				"crm_id": oOutbound['crm_id'],
				"crm_order": oOutbound['crm_order'],
				"type": "Remove Error",
				"memo_user": sesh['memo_id']
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the adhoc record
		iID = oAdHoc.create();

		# Delete the outreach record
		oOutbound.delete()

		# Turn the adhoc instance into a dict
		dAdHoc = oAdHoc.record()

		# Add the names
		dAdHoc['customer_name'] = "%s %s" % (dCustomer['firstName'], dCustomer['lastName'])
		dAdHoc['user_name'] = "%s %s" % (dUser['firstName'], dUser['lastName'])

		# Return the new adhoc data
		return Services.Effect(dAdHoc)

	def outboundReady_update(self, data, sesh):
		"""Outbound Ready

		Updates the ready state of an existing outreach record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_outbound",
			"right": Rights.UPDATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id', 'ready'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oOutbound = Outbound.get(data['_id'])
		if not oOutbound:
			return Services.Effect(error=1104)

		# If there's no order
		if not oOutbound['crm_order'] or oOutbound['crm_order'] == '':
			return Services.Effect(error=1800)

		# Update the ready state
		oOutbound['ready'] = data['ready'] and True or False

		# Save and return the result
		return Services.Effect(
			oOutbound.save()
		)

	def outbounds_read(self, data, sesh):
		"""Outbounds

		Returns all outreach records

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = Services.read('auth', 'rights/verify', {
			"name": "welldyne_outbound",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Fetch all the records joined with the trigger table
		lRecords = Outbound.withTrigger()

		# If we have records
		if lRecords:

			# Find all the customer names
			oEff = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": [d['crm_id'] for d in lRecords]
			}, sesh)
			if oEff.errorExists(): return oEff
			dCustomers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oEff.data.items()}

			# Go through each record and add the customer names
			for d in lRecords:
				d['customer_name'] = d['crm_id'] in dCustomers and dCustomers[d['crm_id']] or 'Unknown'

			# Return all records
			return Services.Effect(lRecords)

		# Else return an empty array
		else:
			return Services.Effect([])

	def stats_read(self, data, sesh):
		"""Stats

		Returns stats about WellDyne

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		return Services.Effect({
			"vs": Trigger.vsShipped()
		})

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
		try: DictHelper.eval(data, ['crm_type', 'crm_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for a trigger with any possible outreach and eligibility
		lTrigger = Trigger.withOutreachEligibility(data['crm_type'], data['crm_id'])

		# If there's nothing
		if not lTrigger:
			return Services.Effect(0)

		# Find the eligibility associated
		dElig = Eligibility.filter({
			"customerId": data['crm_id']
		}, raw=['memberSince', 'memberThru'], limit=1)

		# Add the eligibility to each
		for d in lTrigger:
			d['elig_since'] = dElig and dElig['memberSince'] or None
			d['elig_thru'] = dElig and dElig['memberThru'] or None

		# Return
		return Services.Effect(lTrigger)
