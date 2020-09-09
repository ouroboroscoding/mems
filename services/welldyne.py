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
import os

# Pip imports
import pysftp
from RestOC import Conf, DictHelper, Record_MySQL, Services

# Shared imports
from shared import Excel, Rights

# Records imports
from records.welldyne import \
	AdHoc, AdHocManual, Eligibility, NeverStarted, Outbound, OutboundSent, \
	RxNumber, Trigger

class WellDyne(Services.Service):
	"""WellDyne Service class

	Service for WellDyne, sign in, sign up, etc.
	"""

	_install = [AdHoc, AdHocManual, Outbound, OutboundSent, RxNumber, Trigger]
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
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_adhoc",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['trigger_id', 'type'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the trigger
		dTrigger = Trigger.get(
			data['trigger_id'],
			raw=['crm_type', 'crm_id', 'crm_order', 'raw']
		)

		# If it doesn't exist
		if not dTrigger:
			return Services.Response(error=1104)

		# If we got a trigger, but there's no raw
		if not dTrigger['raw']:

			# Try to create a new instance of the adhoc in the manual table
			try:
				data['memo_user'] = sesh['memo_id']
				oAdHocManual = AdHocManual(data)
			except ValueError as e:
				return Services.Response(error=(1001, e.args[0]))

			# Create the record
			try:
				oAdHocManual.create()

				# Notify developer
				oResponse = Services.create('communications', 'email', {
					"_internal_": Services.internalKey(),
					"text_body": 'https://cs.meutils.com/manualad',
					"subject": 'New Manual AdHoc',
					"to": Conf.get(('developer', 'emails'))
				})
				if oResponse.errorExists(): return oResponse

			# Ignore duplicates, because you know people are gonna click again
			#	and again
			except Record_MySQL.DuplicateException:
				pass

			# Return that we couldn't immediate add the adhoc
			return Services.Response(warning=1801)

		# If the CRM is Konnektive
		if dTrigger['crm_type'] == 'knk':

			# Check the customer exists
			oResponse = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": dTrigger['crm_id']
			}, sesh)
			if oResponse.errorExists(): return oResponse
			dCustomer = oResponse.data

		# Else, invalid CRM
		else:
			return Services.Response(error=1003)

		# Get the user name
		oResponse = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": sesh['memo_id']
		}, sesh)
		if oResponse.errorExists(): return oResponse
		dUser = oResponse.data

		# Try to create a new instance of the adhoc
		try:
			data['memo_user'] = sesh['memo_id']
			oAdHoc = AdHoc(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the record and return the result
		return Services.Response({
			"_id": oAdHoc.create(),
			"crm_type": dTrigger['crm_type'],
			"crm_id": dTrigger['crm_id'],
			"crm_order": dTrigger['crm_order'],
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
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_adhoc",
			"right": Rights.DELETE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oAdHoc = AdHoc.get(data['_id'])
		if not oAdHoc:
			return Services.Response(error=1104)

		# Delete the record and return the result
		return Services.Response(
			oAdHoc.delete()
		)

	def adhocManual_delete(self, data, sesh):
		"""AdHoc Manual Delete

		Transfers the manual adhoc to the primary adhoc table

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "manual_adhoc",
			"right": Rights.DELETE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id', 'raw'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oAdHoc = AdHocManual.get(data['_id'])
		if not oAdHoc:
			return Services.Response(error=(1104, 'adhoc'))

		# Find the trigger
		oTrigger = Trigger.get(oAdHoc['trigger_id'])
		if not oAdHoc:
			return Services.Response(error=(1104, 'trigger'))

		# Update the trigger
		oTrigger['raw'] = data['raw']
		oTrigger.save()

		# Move the adhoc
		oAdHoc.move()

		# Find the user associated
		oResponse = Services.read('monolith', 'users', {
			"_internal_": Services.internalKey(),
			"id": oAdHoc['memo_user'],
			"fields": ["email"]
		}, sesh)
		if oResponse.errorExists(): return oResponse

		# Notify the user
		oResponse = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"text_body": 'Your AdHoc for customer %s, order %s, has been added' % (oTrigger['crm_id'], oTrigger['crm_order']),
			"subject": 'AdHoc Added',
			"to": oResponse.data['email']
		})
		if oResponse.errorExists(): return oResponse

		# Return OK
		return Services.Response(True)

	def adhocManual_read(self, data, sesh):
		"""AdHoc Manual Read

		Returns the list of all AdHoc manual requests

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "manual_adhoc",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch and return all records
		return Services.Response(AdHocManual.display())

	def adhocs_read(self, data, sesh):
		"""Adhocs

		Returns all adhoc records

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_adhoc",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch all the records
		lRecords = AdHoc.display()

		# If we have records
		if lRecords:

			# Find all the customer names
			oResponse = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": [d['crm_id'] for d in lRecords]
			}, sesh)
			if oResponse.errorExists(): return oResponse
			dCustomers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oResponse.data.items()}

			# Find all the user names
			oResponse = Services.read('monolith', 'user/name', {
				"_internal_": Services.internalKey(),
				"id": list(set([d['memo_user'] for d in lRecords]))
			}, sesh)
			if oResponse.errorExists(): return oResponse
			dUsers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oResponse.data.items()}

			# Go through each record and add the customer names
			for d in lRecords:
				d['customer_name'] = d['crm_id'] in dCustomers and dCustomers[d['crm_id']] or 'Unknown'
				sUserId = str(d['memo_user'])
				d['user_name'] = sUserId in dUsers and dUsers[sUserId] or 'Unknown'

		# Return all records
		return Services.Response(lRecords)

	def neverStarted_delete(self, data, sesh):
		"""Neve Started Delete

		Deletes an existing never started record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_never_started",
			"right": Rights.DELETE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oNeverStarted = NeverStarted.get(data['_id'])
		if not oNeverStarted:
			return Services.Response(error=1104)

		# Delete the record and return the result
		return Services.Response(
			oNeverStarted.delete()
		)

	def neverStartedPoll_update(self, data, sesh):
		"""Neve Started Poll

		Attempts to get the latest data from the FTP and add it to the table

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_never_started",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['date'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Get the sFTP and temp file conf
		dSftpConf = Conf.get(('welldyne', 'sftp'))
		sTemp = Conf.get(('temp_folder'))

		# Generate the name of the file
		sFilename = 'Never_Started_%s.xlsx' % data['date']

		# Connect to the sFTP
		with pysftp.Connection(dSftpConf['host'], username=dSftpConf['username'], password=dSftpConf['password']) as oCon:

			# Get the outreach file
			try:
				sGet = '%s/%s' % (sTemp, sFilename)
				oCon.get(sFilename, sGet)
				#oCon.rename(sFilename, 'processed/%s' % sFilename)
			except FileNotFoundError:
				return Services.Response(error=(1803, sFilename))

		# Parse the data
		lData = Excel.parse(sGet, {
			"medication": {"column": 1, "type": Excel.STRING},
			"member_id": {"column": 11, "type": Excel.STRING},
			"reason": {"column": 13, "type": Excel.STRING}
		}, start_row=1)

		print(lData)

		# Go through each line in the file
		for d in lData:

			# Get the actual ID
			sCrmID = d['member_id'].lstrip('0')

			# Find the last trigger associated with the ID
			dTrigger = Trigger.filter({
				"crm_type": 'knk',
				"crm_id": sCrmID,
				"type": {"neq": 'update'}
			}, raw=['crm_order'], orderby=[('_created', 'DESC')], limit=1)

			# Create the instance
			oNeverStarted = NeverStarted({
				"crm_type": 'knk',
				"crm_id": sCrmID,
				"crm_order": dTrigger and dTrigger['crm_order'] or '',
				"medication": d['medication'],
				"reason": d['reason'][:255],
				"ready": False
			})

			# Create the record in the DB
			oNeverStarted.create(conflict='replace')

		# Delete the file
		os.remove(sGet)

		# Return OK
		return Services.Response(True)

	def neverStartedReady_update(self, data, sesh):
		"""Never Started Ready

		Updates the ready state of an existing never started record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_never_started",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id', 'ready'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oNeverStarted = NeverStarted.get(data['_id'])
		if not oNeverStarted:
			return Services.Response(error=1104)

		# If there's no order
		if not oNeverStarted['crm_order'] or oNeverStarted['crm_order'] == '':
			return Services.Response(error=1800)

		# Update the ready state
		oNeverStarted['ready'] = data['ready'] and True or False

		# Save and return the result
		return Services.Response(
			oNeverStarted.save()
		)

	def neverStarteds_read(self, data, sesh):
		"""Never Starteds

		Returns all never started records

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_never_started",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch all the records joined with the trigger table
		lRecords = NeverStarted.withTrigger()

		# If we have records
		if lRecords:

			# Find all the customer names
			oResponse = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": [d['crm_id'] for d in lRecords]
			}, sesh)
			if oResponse.errorExists(): return oResponse
			dCustomers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oResponse.data.items()}

			# Go through each record and add the customer names
			for d in lRecords:
				d['customer_name'] = d['crm_id'] in dCustomers and dCustomers[d['crm_id']] or 'Unknown'

			# Return all records
			return Services.Response(lRecords)

		# Else return an empty array
		else:
			return Services.Response([])

	def outboundAdhoc_update(self, data, sesh):
		"""Outbound OldAdHoc

		Removes a customer from the outbound and puts them as an adhoc / remove
		error record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper adhoc rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_adhoc",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oOutbound = Outbound.get(data['_id'])
		if not oOutbound:
			return Services.Response(error=1104)

		# Look for a trigger with the same info
		dTrigger = Trigger.filter({
			"crm_type": oOutbound['crm_type'],
			"crm_id": oOutbound['crm_id'],
			"crm_order": oOutbound['crm_order']
		}, raw=['_id', 'crm_type', 'crm_id', 'crm_order', 'raw'], limit=1)

		# If there's no tigger
		if not dTrigger:
			return Services.Response(error=1802)

		# Init warning
		iWarning = None

		# If there's no raw data
		if not dTrigger['raw']:

			# Try to create a new instance of the adhoc in the manual table
			try:
				oAdHocManual = AdHocManual({
					"trigger_id": dTrigger['_id'],
					"type": "Remove Error",
					"memo_user": sesh['memo_id']
				})
			except ValueError as e:
				return Services.Response(error=(1001, e.args[0]))

			# Create the record
			try:
				oAdHocManual.create()

				# Delete the outbound record
				oOutbound.delete()

				# Notify developer
				oResponse = Services.create('communications', 'email', {
					"_internal_": Services.internalKey(),
					"text_body": 'https://cs.meutils.com/manualad',
					"subject": 'New Manual AdHoc',
					"to": Conf.get(('developer', 'emails'))
				})
				if oResponse.errorExists(): return oResponse

			# Ignore duplicates, because you know people are gonna click again
			#	and again
			except Record_MySQL.DuplicateException:
				pass

			# Return that we couldn't immediately add the adhoc
			return Services.Response(True, warning=1801)

		# If the CRM is Konnektive
		if oOutbound['crm_type'] == 'knk':

			# Check the customer exists
			oResponse = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": oOutbound['crm_id']
			}, sesh)
			if oResponse.errorExists(): return oResponse
			dCustomer = oResponse.data

		# Else, invalid CRM type
		else:
			return Services.Response(error=1003)

		# Get the user name
		oResponse = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": sesh['memo_id']
		}, sesh)
		if oResponse.errorExists(): return oResponse
		dUser = oResponse.data

		# Try to create a new adhoc instance
		try:
			oAdHoc = AdHoc({
				"trigger_id": dTrigger['_id'],
				"type": "Remove Error",
				"memo_user": sesh['memo_id']
			})
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the adhoc record
		oAdHoc.create();

		# Delete the outbound record
		oOutbound.delete()

		# Turn the adhoc instance into a dict
		dAdHoc = oAdHoc.record()

		# Add the names
		dAdHoc['crm_type'] = dTrigger['crm_type']
		dAdHoc['crm_id'] = dTrigger['crm_id']
		dAdHoc['crm_order'] = dTrigger['crm_order']
		dAdHoc['customer_name'] = "%s %s" % (dCustomer['firstName'], dCustomer['lastName'])
		dAdHoc['user_name'] = "%s %s" % (dUser['firstName'], dUser['lastName'])

		# Return the new adhoc data
		return Services.Response(dAdHoc)

	def outboundReady_update(self, data, sesh):
		"""Outbound Ready

		Updates the ready state of an existing outbound record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_outbound",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id', 'ready'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oOutbound = Outbound.get(data['_id'])
		if not oOutbound:
			return Services.Response(error=1104)

		# If there's no order
		if not oOutbound['crm_order'] or oOutbound['crm_order'] == '':
			return Services.Response(error=1800)

		# Update the ready state
		oOutbound['ready'] = data['ready'] and True or False

		# Save and return the result
		return Services.Response(
			oOutbound.save()
		)

	def outbounds_read(self, data, sesh):
		"""Outbounds

		Returns all outbound records

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "welldyne_outbound",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch all the records joined with the trigger table
		lRecords = Outbound.withTrigger()

		# If we have records
		if lRecords:

			# Find all the customer names
			oResponse = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": [d['crm_id'] for d in lRecords]
			}, sesh)
			if oResponse.errorExists(): return oResponse
			dCustomers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oResponse.data.items()}

			# Go through each record and add the customer names
			for d in lRecords:
				d['customer_name'] = d['crm_id'] in dCustomers and dCustomers[d['crm_id']] or 'Unknown'

			# Return all records
			return Services.Response(lRecords)

		# Else return an empty array
		else:
			return Services.Response([])

	def stats_read(self, data, sesh):
		"""Stats

		Returns stats about WellDyne

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		return Services.Response({
			"vs": Trigger.vsShipped()
		})

	def triggerInfo_read(self, data, sesh):
		"""Trigger Info

		Returns the last trigger associated with the customer, including any
		possible outbound and eligibility

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		#oResponse = Services.read('auth', 'rights/verify', {
		#	"name": "welldyne",
		#	"right": Rights.READ
		#}, sesh)
		#if not oResponse.data:
		#	return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['crm_type', 'crm_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, "missing") for f in e.args]))

		# Look for a trigger with any possible outbound and eligibility
		lTrigger = Trigger.withOutreachEligibility(data['crm_type'], data['crm_id'])

		# If there's nothing
		if not lTrigger:
			return Services.Response(0)

		# Find the eligibility associated
		dElig = Eligibility.filter({
			"customerId": data['crm_id']
		}, raw=['memberSince', 'memberThru'], limit=1)

		# Add the eligibility to each
		for d in lTrigger:
			d['elig_since'] = dElig and dElig['memberSince'] or None
			d['elig_thru'] = dElig and dElig['memberThru'] or None

		# Return
		return Services.Response(lTrigger)
