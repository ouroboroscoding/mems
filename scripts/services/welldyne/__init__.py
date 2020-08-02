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
from io import StringIO
from time import time
import uuid

# Pip imports
import arrow
import pysftp
from RestOC import Conf, DictHelper, Errors, Services, Sesh

# Shared imports
from shared import Rights

# Service imports
from .records import AdHoc, AdHocSent, Eligibility, Outbound, OutboundSent, \
						Trigger, \
						OldAdHoc, OldOutreach, OldTrigger

class WellDyne(Services.Service):
	"""WellDyne Service class

	Service for WellDyne, sign in, sign up, etc.
	"""

	_install = [AdHoc, AdHocSent, Outbound, OutboundSent, Trigger]
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

	@classmethod
	def __dateDigits(cls, date):
		"""Date Digits

		Returns just the digits of a date

		Arguments:
			date (str): The date as a string

		Returns:
			str
		"""
		return '%s%s%s' % (date[0:4], date[5:7], date[8:10])

	@classmethod
	def _eligibilityGenerateAndUpload(cls, time):
		"""ELigibility Generate And Upload

		Fetches the valid eligibility, generates a report, and uploads it to
		the sFTP for WellDyne to consume

		Arguments:
			time (str): The time to append to the name of the uploaded file

		Returns:
			None
		"""

		# Find all records that have a member through date
		lRecords = Eligibility.withCustomerData()

		# Init the list of lines
		lLines = []

		# Go through each record and generate the line
		for d in lRecords:
			lLines.append(''.join([
				'ED'.ljust(15),										# Group ID
				str(d['customerId']).zfill(6).ljust(18),			# Member ID
				'00',												# Person code
				'1',												# Relationship
				(d['shipLastName'] or '')[0:25].ljust(25),			# Last Name
				(d['shipFirstName'] or '')[0:15].ljust(15),			# First Name
				' ',												# Middle initial
				'M',												# Sex
				cls.__dateDigits(d['dob'] or '').ljust(8),			# DOB
				' ',												# Multiple Birth Code
				'                  ',								# DurKey
				'         ',										# Unique ID for Accums
				(d['shipAddress1'] or '')[0:40].ljust(40),			# Address 1
				(d['shipAddress2'] or '')[0:40].ljust(40),			# Address 2
				'                                        ',			# Address 3
				(d['shipCity'] or '')[0:20].ljust(20),				# City
				(d['shipState'] or '')[0:2].ljust(2),				# State
				(d['shipPostalCode'] or '')[0:5].ljust(5),			# Zip 5
				'    ',												# Zip 5 + 4
				'  ',												# Zip 5 + 4 + 2
				(d['phoneNumber'] or '')[-10:].ljust(10),			# Phone
				' ',												# Family Flag
				' ',												# Family Type
				'                  ',								# Family ID
				'        ',											# Benefit Reset Date
				cls.__dateDigits(d['memberSince']).ljust(8),		# Member From Date
				cls.__dateDigits(d['memberThru']).ljust(8),			# Member Thru Date
				'               ',									# PCP ID
				'  ',												# PCP ID Qualifier
				'  ',												# PCP ID State
				' ',												# Alt Ins Flag
				'          ',										# Alt Ins Code
				'        ',											# Alt Ins From Date
				'        ',											# Alt Ins Thru Date
				'                  ',								# Unique Patient ID
				'                    ',								# Diagnosis Code 1
				'        ',											# Diagnosis Code 1 From Date
				'        ',											# Diagnosis Code 1 Thru Date
				'  ',												# Qualifier 1
				'                    ',								# Diagnosis Code 2
				'        ',											# Diagnosis Code 2 From Date
				'        ',											# Diagnosis Code 2 Thru Date
				'  ',												# Qualifier 2
				'                    ',								# Diagnosis Code 3
				'        ',											# Diagnosis Code 3 From Date
				'        ',											# Diagnosis Code 3 Thru Date
				'  ',												# Qualifier 3
				(d['emailAddress'] or '')[0:50].ljust(50),			# E-mail address
				'           '										# ID Card Template
		]))

		# Generate the filename with the current date
		sDate = '%s%s' % (arrow.get().format('YYYYMMDD'), time)
		sFilename = 'RWTMEXCEL%s.TXT' % sDate;

		# Get the sFTP config
		dSFTP = Conf.get(('welldyne', 'sftp'))

		# Pull off the subdirectory if there is one
		sFolder = dSFTP.pop('folder', None)
		if sFolder:
			sFilename = '%s/%s' % (sFolder, sFilename)

		# Upload the file to the sFTP
		with pysftp.Connection(**dSFTP) as oCon:
			oCon.putfo(StringIO('\n'.join(lLines)), sFilename)

	def oldAdhoc_create(self, data, sesh):
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
			oOldAdHoc = OldAdHoc(data)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record and return the result
		return Services.Effect({
			"id": oOldAdHoc.create(),
			"customerName": '%s %s' % (dCustomer['firstName'], dCustomer['lastName']),
			"userName": '%s %s' % (dUser['firstName'], dUser['lastName'])
		})

	def oldAdhoc_delete(self, data, sesh):
		"""OldAdHoc Delete

		Deletes an existing record from the OldAdHoc report

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
		oOldAdHoc = OldAdHoc.get(data['id'])
		if not oOldAdHoc:
			return Services.Effect(error=1104)

		# Delete the record and return the result
		return Services.Effect(
			oOldAdHoc.delete()
		)

	def oldAdhocs_read(self, data, sesh):
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
		lRecords = OldAdHoc.get(raw=['id', 'customerId', 'type', 'user'])

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

	def oldOutreach_delete(self, data, sesh):
		"""OldOutreach Delete

		Deletes an existing record from the OldOutreach report

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
		oOldOutreach = OldOutreach.get(data['id'])
		if not oOldOutreach:
			return Services.Effect(error=1104)

		# Delete the record and return the result
		return Services.Effect(
			oOldOutreach.delete()
		)

	def oldOutreachAdhoc_update(self, data, sesh):
		"""OldOutreach OldAdHoc

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
		oOldOutreach = OldOutreach.get(data['id'])
		if not oOldOutreach:
			return Services.Effect(error=1104)

		# Check the customer exists
		oEff = Services.read('monolith', 'customer/name', {
			"customerId": str(oOldOutreach['customerId'])
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
			oOldAdHoc = OldAdHoc({
				"customerId": oOldOutreach['customerId'],
				"type": "Remove Error",
				"user": sesh['memo_id'],
				"createdAt": sDT,
				"updatedAt": sDT
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the adhoc record
		iID = oOldAdHoc.create();

		# Delete the outreach record
		oOldOutreach.delete()

		# Turn the adhoc instance into a dict
		dOldAdHoc = oOldAdHoc.record()

		# Add the names
		dOldAdHoc['customerName'] = "%s %s" % (dCustomer['firstName'], dCustomer['lastName'])
		dOldAdHoc['userName'] = "%s %s" % (dUser['firstName'], dUser['lastName'])

		# Return the new adhoc data
		return Services.Effect(dOldAdHoc)

	def oldOutreachReady_update(self, data, sesh):
		"""OldOutreach Ready

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
		oOldOutreach = OldOutreach.get(data['id'])
		if not oOldOutreach:
			return Services.Effect(error=1104)

		# Update the ready state
		oOldOutreach['ready'] = data['ready'] and True or False

		# Save and return the result
		return Services.Effect(
			oOldOutreach.save()
		)

	def oldOutreachs_read(self, data, sesh):
		"""OldOutreachs

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
		lRecords = OldOutreach.witdhOlTrigger()

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

	def oldStats_read(self, data, sesh):
		"""Stats

		Returns stats about WellDyne

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		return Services.Effect({
			"vs": OldTrigger.vsShipped()
		})

	def oldTriggerInfo_read(self, data, sesh):
		"""OldTrigger Info

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
		dOldTrigger = OldTrigger.withOutreachEligibility(data['customerId'])

		# If there's nothing
		if not dOldTrigger:
			dOldTrigger = 0

		# Return
		return Services.Effect(dOldTrigger)
