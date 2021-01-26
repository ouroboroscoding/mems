# coding=utf8
""" Monolith Service

Handles all Monolith requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-04-26"

# Python imports
import re
from time import time

# Pip imports
import arrow
import bcrypt
from redis import StrictRedis
from RestOC import Conf, DictHelper, Errors, Record_MySQL, Services, \
					StrHelper, Templates

# Shared imports
from shared import Memo, Rights, SMSWorkflow, Sync

# Records imports
from records.monolith import \
	Calendly, CalendlyEvent, \
	Campaign, \
	CustomerClaimed, CustomerClaimedLast, \
	CustomerCommunication, CustomerMsgPhone, \
	DsPatient, \
	Forgot, \
	HrtLabResultTests, \
	KtCustomer, KtOrder, KtOrderClaim, KtOrderClaimLast, KtOrderContinuous, \
	ShippingInfo, \
	SmpNote, SmpOrderStatus, SmpState, \
	SMSStop, SMSStopChange, \
	TfAnswer, TfLanding, TfQuestion, TfQuestionOption, \
	User, \
	init as recInit

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

class Monolith(Services.Service):
	"""Monolith Service class

	Service for Monolith, sign in, sign up, etc.
	"""

	_install = []
	"""Record types called in install"""

	_TRACKING_LINKS = {
		"FDX": "http://www.fedex.com/Tracking?tracknumbers=%s",
		"UPS": "https://www.ups.com/track?tracknum=%s",
		"USPS": "https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1=%s"
	}
	"""Tracking links"""

	_DECLINE_NOTES = {
		'Medical': 'Order declined for medical reasons.',
		'Duplicate Order': 'Order declined due to duplicate.',
		'Current Customer': 'Order declined at customer\'s request.',
		'Contact Attempt': 'Order declined because customer can not be reached.'
	}
	"""Decline Notes"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Init the records
		recInit()

		# Create a connection to Redis
		self._redis = StrictRedis(**Conf.get(('redis', 'primary'), {
			"host": "localhost",
			"port": 6379,
			"db": 0
		}))

		# Init the Sync module
		Sync.init()

		# Store conf
		self._conf = Conf.get(('services', 'monolith'))

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

	def agentClaim_delete(self, data, sesh):
		"""Agent Claim Delete

		Deletes an existing claim

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_overwrite",
			"right": Rights.DELETE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the claim
		oClaim = CustomerClaimed.get(data['phoneNumber'])
		if not oClaim:
			return Services.Response(error=1104)

		# Store the agent ID
		iAgent = oClaim['user']

		# Delete the claim
		if oClaim.delete():

			# Notify the agent they lost the claim
			Sync.push('monolith', 'user-%s' % str(iAgent), {
				"type": 'claim_removed',
				"phoneNumber": data['phoneNumber']
			})

			# Return OK
			return Services.Response(True)

		# Failed
		return Services.Response(False)

	def agentClaims_read(self, data, sesh):
		"""Agent Claims

		Returns all claims by all agents currently in the system

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_overwrite",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch all the current claims
		lClaims = CustomerClaimed.get(raw=True, orderby=[['createdAt', 'DESC']])

		# If there's nothing, return nothing
		if not lClaims:
			return Services.Response([])

		# Get a list of all the user IDs
		lUserIDs = set()
		for d in lClaims:
			lUserIDs.add(d['user'])
			if d['provider']: lUserIDs.add(d['provider'])
			if d['transferredBy']:
				d['transferredBy'] = int(d['transferredBy'])
				lUserIDs.add(d['transferredBy'])

		# Get the names of all the users
		dUsers = {
			d['id']: '%s %s' % (d['firstName'], d['lastName'])
			for d in User.get(list(lUserIDs), raw=['id', 'firstName', 'lastName'])
		}

		# Go through each claim and update the name accordingly
		for d in lClaims:
			d['user'] = d['user'] in dUsers and dUsers[d['user']] or 'N/A'
			if d['provider']:
				d['provider'] = d['provider'] in dUsers and dUsers[d['provider']] or 'N/A'
			else:
				d['provider'] = ''
			if d['transferredBy']:
				d['transferredBy'] = d['transferredBy'] in dUsers and dUsers[d['transferredBy']] or 'N/A'
			else:
				d['transferredBy'] = ''

		# Return the list of claims
		return Services.Response(lClaims)

	def calendlyEvent_create(self, data, sesh):
		"""Calendly Event Create

		Creates a new calendly event associated with a record in calendly

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'calendly_admin', Rights.CREATE)

		# Create a new instance
		try:
			oCalendlyEvent = CalendlyEvent(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# If both the state and the provider is empty, there's an issue
		if 'state' not in data and 'provider' not in data:
			return Services.Error(1516)

		# Create the record and get the ID
		try:
			return Services.Response(
				oCalendlyEvent.create()
			)
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

	def calendlyEvent_delete(self, data, sesh):
		"""Calendly Event Delete

		Deletes an existing calendly event associated with a record in calendly,
		does not delete the event in Calendly itself

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'calendly_admin', Rights.DELETE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oCalendlyEvent = CalendlyEvent.get(data['id'])

		# Delete the record and return the result
		return Services.Response(
			oCalendlyEvent.delete()
		)

	def calendlyEvent_read(self, data, sesh):
		"""Calendly Event Read

		Fetches an existing calendly event associated with a record in calendly

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'calendly_admin', Rights.READ)

		# Verify minimum fields
		try: DictHelper.eval(data, ['id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		dCalendlyEvent = CalendlyEvent.get(data['id'], raw=True)
		if not dCalendlyEvent:
			return Services.Error(1104)

		# Return the product
		return Services.Response(dCalendlyEvent)

	def calendlyEvent_update(self, data, sesh):
		"""Calendly Event Update

		Updates an existing calendly event associated with a record in calendly,
		does not update the record in Calendly itself

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper rights
		Rights.check(sesh, 'calendly_admin', Rights.UPDATE)

		# Find the record
		oCalendlyEvent = CalendlyEvent.get(data['id'])

		# Remove fields that can't be changed
		del data['id']
		if 'createdAt' in data: del data['createdAt']
		if 'updatedAt' in data: del data['updatedAt']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oCalendlyEvent[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Error(1001, lErrors)

		# If both the state and the provider is empty, there's an issue
		if 'state' not in oCalendlyEvent and 'provider' not in oCalendlyEvent:
			return Services.Error(1516)

		# Update the record and return the result
		return Services.Response(
			oCalendlyEvent.save()
		)

	def calendlyEvents_read(self, data, sesh):
		"""Calendly Events Read

		Fetches all existing calendly events associated with records in calendly

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'calendly_admin', Rights.READ)

		# Return all records
		return Services.Response(
			CalendlyEvent.get(raw=True, orderby='name')
		)

	def customerCalendly_read(self, data, sesh):
		"""Customer Calendly

		Fetches all Calendly appointments that can be found associated with
		either the customer's email or phone number

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "calendly",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Fetch all appointments associated with the customer and return them
		return Services.Response(
			Calendly.byCustomer(data['customerId'])
		)

	def customerClaim_create(self, data, sesh):
		"""Customer Claim Create

		Stores a record to claim a customer conversation for a user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_claims",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If not order ID was passed
		if 'orderId' not in data:
			data['orderId'] = None

		# If no provider was passed
		if 'provider' not in data:
			data['provider'] = None

		# If continuous was not passed
		if 'continuous' not in data:
			data['continuous'] = None

		# Check how many claims this user already has
		iCount = CustomerClaimed.count(filter={
			"user": sesh['memo_id']
		})

		# If they're at or more than the maximum
		if iCount >= sesh['claims_max']:
			return Services.Response(error=1504)

		# Make sure we have a customer conversation
		dConvo = CustomerMsgPhone.filter({
			"customerPhone": [data['phoneNumber'], '1%s' % data['phoneNumber']]
		}, raw=['id'])
		if not dConvo:

			# Find the customer by phone number
			dCustomer = KtCustomer.filter(
				{"phoneNumber": [data['phoneNumber'], '1%s' % data['phoneNumber']]},
				raw=['firstName', 'lastName'],
				orderby=[['updatedAt', 'DESC']],
				limit=1
			)

			# If we can't find one
			if not dCustomer:
				return Services.Response(error=1508)

			# Get current time
			sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

			# Create a new convo
			oConvo = CustomerMsgPhone({
				"customerPhone": data['phoneNumber'],
				"customerName": '%s %s' % (dCustomer['firstName'], dCustomer['lastName']),
				"lastMsgAt": sDT,
				"hiddenFlag": 'N',
				"totalIncoming": 0,
				"totalOutGoing": 0,
				"createdAt": sDT,
				"updatedAt": sDT
			})
			oConvo.create()

		# Attempt to create the record
		try:
			oCustomerClaimed = CustomerClaimed({
				"phoneNumber": data['phoneNumber'],
				"user": sesh['memo_id'],
				"orderId": data['orderId'],
				"continuous": data['continuous'],
				"provider": data['provider'],
				"viewed": True
			})
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Try to create the record and return the result
		try:
			return Services.Response(
				oCustomerClaimed.create()
			)

		# If we got a duplicate exception
		except Record_MySQL.DuplicateException:

			# Fine the user who claimed it
			dClaim = CustomerClaimed.get(data['phoneNumber'], raw=['user']);

			# Return the error with the user ID
			return Services.Response(error=(1101, dClaim['user']))

	def customerClaim_delete(self, data, sesh):
		"""Customer Claim Delete

		Deletes a record to claim a customer conversation by a user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_claims",
			"right": Rights.DELETE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the claim
		oClaim = CustomerClaimed.get(data['phoneNumber'])
		if not oClaim:
			return Services.Response(error=1104)

		# If the user is not the one who made the claim
		if oClaim['user'] != sesh['memo_id']:
			return Services.Response(error=Rights.INVALID)

		# Delete the claim and return the response
		return Services.Response(
			oClaim.delete()
		)

	def customerClaim_update(self, data, sesh):
		"""Customer Claim Update

		Switches a claim to another agent

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_claims",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber', 'user_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the claim
		oClaim = CustomerClaimed.get(data['phoneNumber'])
		if not oClaim:
			return Services.Response(error=(1104, data['phoneNumber']))

		# If the current owner of the claim is not the person transfering,
		#	check permissions
		if oClaim['user'] != sesh['memo_id']:

			# Make sure the user has the proper rights
			oResponse = Services.read('auth', 'rights/verify', {
				"name": "csr_overwrite",
				"right": Rights.CREATE
			}, sesh)
			if not oResponse.data:
				return Services.Response(error=Rights.INVALID)

			# Store the old user
			iOldUser = oClaim['user']

		# Else, no old user
		else:
			iOldUser = None

		# Find the user
		if not User.exists(data['user_id']):
			return Services.Response(error=(1104, data['user_id']))

		# Switch the user associated to the logged in user
		oClaim['user'] = data['user_id']
		oClaim['transferredBy'] = sesh['memo_id']
		oClaim['viewed'] = False
		oClaim.save()

		# If the user transferred it to themselves, they don't need a
		#	notification
		if data['user_id'] != sesh['memo_id']:

			# Sync the transfer for anyone interested
			Sync.push('monolith', 'user-%s' % str(data['user_id']), {
				"type": 'claim_transfered',
				"claim": {
					"phoneNumber": data['phoneNumber'],
					"orderId": oClaim['orderId'],
					"provider": oClaim['provider'],
					"transferredBy": sesh['memo_id'],
					"viewed": False
				}
			})

		# If the claim was forceable removed
		if iOldUser:

			# Notify the user they lost the claim
			Sync.push('monolith', 'user-%s' % str(iOldUser), {
				"type": 'claim_removed',
				"phoneNumber": oClaim['phoneNumber']
			})

		# Return OK
		return Services.Response(True)

	def customerClaimView_update(self, data, sesh):
		"""Customer Claim View

		Marks the claim as viewed for the first time

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_claims",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the claim
		oClaim = CustomerClaimed.get(data['phoneNumber'])
		if not oClaim:
			return Services.Response(error=(1104, data['phoneNumber']))

		# If the current owner of the claim is not the person clearing, return
		#	an error
		if oClaim['user'] != sesh['memo_id']:
			return Services.Response(error=1000)

		# Mark the viewed flag
		oClaim['viewed'] = True
		oClaim.save()

		# Return OK
		return Services.Response(True)

	def customerDob_read(self, data, sesh):
		"""Customer DoseSpot ID

		Returns the ID of the DoseSpote patient based on their customer ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "memo_mips",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the customer by ID
		dCustomer = KtCustomer.filter(
			{"customerId": data['customerId']},
			raw=['lastName', 'emailAddress', 'phoneNumber'],
			orderby=[('dateUpdated', 'DESC')],
			limit=1
		)

		# If there's no customer
		if not dCustomer:
			return Services.Response(error=1104)

		# Try to find the landing based on customer details
		lLandings = TfLanding.find(
			dCustomer['lastName'],
			dCustomer['emailAddress'] or '',
			dCustomer['phoneNumber'],
			['MIP-A1', 'MIP-A2', 'MIP-H1', 'MIP-H2']
		)

		# If there's no mip
		if not lLandings:
			return Services.Response(False)

		# Find the dob
		sDOB = TfAnswer.dob(lLandings[0]['landing_id'])

		# If it's not found
		if not sDOB:
			return Services.Response(False)

		# Return the DOB
		return Services.Response(sDOB)

	def customerDsid_create(self, data, sesh):
		"""Customer DoseSpot ID Create

		Creates a new patient in DoseSpot and returns the ID generated

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'clinician_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the customer in Konnektive
		oResponse = Services.read('konnektive', 'customer', {
			"customerId": data['customerId']
		}, sesh)
		if oResponse.errorExists(): return oResponse
		dCustomer = oResponse.data

		# Make sure we don't already have the patient record
		dDsPatient = DsPatient.filter({
			"customerId": str(data['customerId'])
		}, raw=['id'], limit=1)
		if dDsPatient:
			return Services.Response(error=1101)

		# Get the latest landing
		lLandings = TfLanding.find(
			dCustomer['shipping']['lastName'],
			dCustomer['email'] or '',
			dCustomer['phone'],
			['MIP-A1', 'MIP-A2', 'MIP-H1', 'MIP-H2']
		)
		if not lLandings:
			return Services.Response(error=(1104, 'mip'))

		# Get the DOB
		sDOB = TfAnswer.dob(lLandings[0]['landing_id'])
		if not sDOB:
			return Services.Response(error=1910)

		# Try to create the DsInstance to check field values
		try:
			sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')
			dData = {
				"customerId": str(dCustomer['customerId']),
				"firstName": dCustomer['shipping']['firstName'] and dCustomer['shipping']['firstName'][:35],
				"lastName": dCustomer['shipping']['lastName'] and dCustomer['shipping']['lastName'][:35],
				"dateOfBirth": sDOB,
				"gender": '1',
				"email": dCustomer['email'] and dCustomer['email'][:255],
				"address1": dCustomer['shipping']['address1'] and dCustomer['shipping']['address1'][:35],
				"address2": dCustomer['shipping']['address2'] and dCustomer['shipping']['address2'][:35],
				"city": dCustomer['shipping']['city'] and dCustomer['shipping']['city'][:35],
				"state": dCustomer['shipping']['state'] and dCustomer['shipping']['state'][:35],
				"zipCode": dCustomer['shipping']['postalCode'] and dCustomer['shipping']['postalCode'][:10],
				"primaryPhone": dCustomer['phone'] and dCustomer['phone'][:25],
				"primaryPhoneType": '4',
				"active": 'Y',
				"createdAt": sDT,
				"updatedAt": sDT
			}
			oDsPatient = DsPatient(dData)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Send the data to the prescriptions service to get the patient ID
		oResponse = Services.create('prescriptions', 'patient', {
				"patient": dData,
				"clinician_id": data['clinician_id']
		}, sesh)
		if oResponse.errorExists():
			return oResponse

		# Store the patient ID
		iPatientId = oResponse.data

		# If we got a default pharmacy
		if 'pharmacy_id' in data:

			# Add the pharmacy to the patient
			oResponse = Services.create('prescriptions', 'patient/pharmacy', {
				"patient_id": iPatientId,
				"pharmacy_id": data['pharmacy_id'],
				"clinician_id": data['clinician_id']
			}, sesh)
			if oResponse.errorExists():
				return oResponse

		# Add the patient ID and save the record
		try:
			oDsPatient['patientId'] = str(iPatientId)
			oDsPatient.create()
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

		# Return the ID
		return Services.Response(iPatientId)

	def customerDsid_read(self, data, sesh):
		"""Customer DoseSpot ID

		Returns the ID of the DoseSpote patient based on their customer ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the patient ID
		dPatient = DsPatient.filter(
			{"customerId": str(data['customerId'])},
			raw=['patientId'],
			limit=1
		)

		# If there's no patient
		if not dPatient:
			return Services.Response(0)

		# Return the ID
		return Services.Response(int(dPatient['patientId']))

	def customerDsid_update(self, data, sesh):
		"""Customer DoseSpot ID Update

		Updates an existing patient in DoseSpot

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'clinician_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the patient record
		oDsPatient = DsPatient.filter({
			"customerId": str(data['customerId'])
		}, limit=1)
		if not oDsPatient:
			return Services.Response(error=(1104, 'patient'))

		# Find the customer in Konnektive
		oResponse = Services.read('konnektive', 'customer', {
			"customerId": data['customerId']
		}, sesh)
		if oResponse.errorExists():
			if oResponse.error['code'] == 1104:
				oResponse.error['msg'] = 'konnektive'
			return oResponse

		# Store the customer data
		dCustomer = oResponse.data

		# Look for a landing by customerId
		dLanding = TfLanding.filter({
			"ktCustomerId": str(data['customerId']),
			"formId": ['MIP-A1', 'MIP-A2', 'MIP-H1', 'MIP-H2']
		}, raw=['landing_id'], limit=1, orderby=[['submitted_at', 'DESC']])

		# If there's no landing
		if not dLanding:

			# Get the latest landing
			lLandings = TfLanding.find(
				dCustomer['shipping']['lastName'],
				dCustomer['email'] or '',
				dCustomer['phone'],
				['MIP-A1', 'MIP-A2', 'MIP-H1', 'MIP-H2']
			)
			if not lLandings:
				return Services.Response(error=(1104, 'mip'))

			# Store the latest
			dLanding = lLandings[0]

		# Get the DOB
		sDOB = TfAnswer.dob(dLanding['landing_id'])
		if not sDOB:
			return Services.Response(error=1910)

		# Try to update the fields
		try:
			sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')
			oDsPatient['firstName'] = dCustomer['shipping']['firstName'] and dCustomer['shipping']['firstName'][:35];
			oDsPatient['lastName'] = dCustomer['shipping']['lastName'] and dCustomer['shipping']['lastName'][:35];
			oDsPatient['dateOfBirth'] = sDOB;
			oDsPatient['email'] = dCustomer['email'] and dCustomer['email'][:255];
			oDsPatient['address1'] = dCustomer['shipping']['address1'] and dCustomer['shipping']['address1'][:35];
			oDsPatient['address2'] = dCustomer['shipping']['address2'] and dCustomer['shipping']['address2'][:35];
			oDsPatient['city'] = dCustomer['shipping']['city'] and dCustomer['shipping']['city'][:35];
			oDsPatient['state'] = dCustomer['shipping']['state'] and dCustomer['shipping']['state'][:35];
			oDsPatient['zipCode'] = dCustomer['shipping']['postalCode'] and dCustomer['shipping']['postalCode'][:10];
			oDsPatient['primaryPhone'] = dCustomer['phone'] and dCustomer['phone'][:25];
			oDsPatient['updatedAt'] = sDT
			oDsPatient.save()
		except ValueError as e:
			return Services.Response(error=(1001, [e.args[0]]))

		# Send the data to the prescriptions service to get the patient ID
		oResponse = Services.update('prescriptions', 'patient', {
			"patient": {
				"id": int(oDsPatient['patientId']),
				"firstName": dCustomer['shipping']['firstName'],
				"lastName": dCustomer['shipping']['lastName'],
				"dateOfBirth": sDOB,
				"gender": '1',
				"email": dCustomer['email'],
				"address1": dCustomer['shipping']['address1'],
				"address2": dCustomer['shipping']['address2'],
				"city": dCustomer['shipping']['city'],
				"state": dCustomer['shipping']['state'],
				"zipCode": dCustomer['shipping']['postalCode'],
				"primaryPhone": dCustomer['phone'],
				"primaryPhoneType": '4',
				"active": 'Y'
			},
			"clinician_id": data['clinician_id']
		}, sesh)

		# Return the response
		return oResponse

	def customerExists_read(self, data, sesh):
		"""Customer Exists

		Returns bool based on existing of customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Return whether the customer exists or not
		return Services.Response(
			KtCustomer.exists(data['customerId'], 'customerId')
		)

	def customerHide_update(self, data, sesh):
		"""Customer Hide

		Marks a customer conversation as hidden

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerPhone'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Update the records hidden field
		CustomerMsgPhone.updateField('hiddenFlag', 'Y', filter={"customerPhone": data['customerPhone']})

		# Return OK
		return Services.Response(True)

	def customerHrtLabs_read(self, data, sesh):
		"""Customer HRT Lab Results

		Fetches a customer's HRT lab test results

		Arguments:
			data (dict): Data sent with request
			sesh (Sesh._Session): THe session associated with the request

		Returns:
			Services.Response
		"""
		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "memo_mips",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

			# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Fetch and return the customer's HRT lab test results
		return Services.Response(
			HrtLabResultTests.filter({
				"customerId": data['customerId']
			}, raw=True)
		)

	def customerIdByPhone_read(self, data, sesh):
		"""Customer ID By Phone

		Fetches a customer's ID by their phone number

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the latest customer with the given number
		dRes = KtCustomer.byPhone(data['phoneNumber'])

		# If there's no customer
		if not dRes:
			return Services.Response(0)

		# Return the ID
		return Services.Response(dRes)

	def customerMessages_read(self, data, sesh):
		"""Customer Messages

		Fetches all messages associated with a customer (phone number)

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerPhone'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Get the messages
		lMsgs = CustomerCommunication.thread(data['customerPhone'])

		# Get the type
		sType = len(KtOrder.ordersByPhone(data['customerPhone'])) and 'support' or 'sales'

		# Find out if the user is blocked anywhere
		bStop = SMSStop.filter({"phoneNumber": data['customerPhone'], "service": sType}) and True or False

		# Fetch and return all the messages associated with the number
		return Services.Response({
			"messages": CustomerCommunication.thread(data['customerPhone']),
			"stop": bStop,
			"type": sType
		})

	def customerMips_read(self, data, sesh):
		"""Customer MIPs

		Fetches the medical intake path questions/answers associated with a
		customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "memo_mips",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If we want all forms
		if 'form' not in data or data['form'] == 'all':
			data['form'] = None

		# Init the landing filter
		dFilter = {
			"ktCustomerId": data['customerId']
		}

		# If we have a request for specific forms
		if data['form']:
			dFilter['formId'] = data['form']

		# Find the MIPs by customer ID
		lLandings = TfLanding.filter(
			dFilter,
			raw=['landing_id', 'formId', 'submitted_at', 'complete'],
			orderby=[['submitted_at', 'DESC']]
		)

		# If we found none, fall back to the old format just to see if we get
		#	anything
		if not lLandings:

			# Find the customer by ID
			dCustomer = KtCustomer.filter(
				{"customerId": data['customerId']},
				raw=['lastName', 'emailAddress', 'phoneNumber'],
				limit=1
			)

			# Try to find the landing
			lLandings = TfLanding.find(
				dCustomer['lastName'],
				dCustomer['emailAddress'] or '',
				dCustomer['phoneNumber'],
				data['form']
			)

			# If there's no mips
			if not lLandings:
				return Services.Response(0)

		# Init the return
		lRet = []

		# Go through each landing found
		for dLanding in lLandings:

			# Init the data
			dData = {
				"id": dLanding['landing_id'],
				"form": dLanding['formId'],
				"date": dLanding['submitted_at'],
				"completed": dLanding['complete'] == 'Y'
			}

			# Get the questions associated with the landing form
			dData['questions'] = TfQuestion.filter(
				{"formId": dLanding['formId'], "activeFlag": 'Y'},
				raw=['ref', 'title', 'type'],
				orderby='questionNumber'
			)

			# Get the options for the questions
			lOptions = TfQuestionOption.filter(
				{"questionRef": [d['ref'] for d in dData['questions']], "activeFlag": 'Y'},
				raw=['questionRef', 'displayOrder', 'option'],
				orderby=['questionRef', 'displayOrder']
			)

			# Create lists of options by question
			dData['options'] = {}
			for d in lOptions:
				try: dData['options'][d['questionRef']].append(d['option'])
				except KeyError: dData['options'][d['questionRef']] = [d['option']]

			# Fetch the answers
			dAnswers = {
				d['ref']: d['value']
				for d in TfAnswer.filter(
					{"landing_id": dLanding['landing_id']},
					raw=['ref', 'value']
				)
			}

			# Match the answer to the questions
			for d in dData['questions']:
				d['answer'] = d['ref'] in dAnswers and \
								dAnswers[d['ref']] or \
								''
				if d['type'] == 'yes_no' and d['answer'] in ['0', '1']:
					d['answer'] = d['answer'] == '1' and 'Yes' or 'No'

			# Add the data to the return list
			lRet.append(dData)

		# Return the landings
		return Services.Response(lRet)

	def customerMipAnswer_update(self, data, sesh):
		"""Customer MIP Answer Update

		Updates the answer to a single MIP question

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "memo_mips",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['landing_id', 'ref', 'value'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the answer
		oTfAnswer = TfAnswer.filter({
			"landing_id": data['landing_id'],
			"ref": data['ref']
		}, limit=1)

		# If it's found
		if oTfAnswer:

			# Update the value
			try:
				oTfAnswer['value'] = data['value']
				mRes = oTfAnswer.save()
			except ValueError as e:
				return Services.Response(error=(1001, [e.args[0]]))

		# Else, if it's not found
		else:

			# Find the landing in order to get the form type
			dTfLanding = TfLanding.filter({
				"landing_id": data['landing_id']
			}, raw=['formId'], limit=1)
			if not dTfLanding:
				return Services.Response(error=(1104, 'landing'))

			# Find the question in order to get the questionId and type
			dTfQuestion = TfQuestion.filter({
				"formId": dTfLanding['formId'],
				"ref": data['ref']
			}, raw=['questionId', 'type'], limit=1)
			if not dTfQuestion:
				return Services.Response(error=(1104, 'question'))

			# Create the answer
			try:
				sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')
				oTfAnswer = TfAnswer({
					"landing_id": data['landing_id'],
					"ref": data['ref'],
					"questionId": dTfQuestion['questionId'],
					"type": dTfQuestion['type'],
					"value": data['value'],
					"createdAt": sDT,
					"updatedAt": sDT
				})
				mRes = oTfAnswer.create()
			except ValueError as e:
				return Services.Response(error=(1001, e.args[0]))

		# If it's DOB
		if data['ref'] in ['b63763bc7f3b71dc', 'birthdate']:

			# Find the landing
			lLandings = TfLanding.filter({
				"landing_id": data['landing_id']
			})

			# Update DOB for each
			for o in lLandings:
				o['birthDay'] = data['value']
				o.save()

		# Return the result of the update/create
		return Services.Response(mRes)

	def customerName_read(self, data, sesh):
		"""Customer Name

		Fetchs one or more names based on IDs, returns as a dictionary (one ID)
		or of ID to name (multiple IDs)

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# If there's only one
		if isinstance(data['customerId'], str):
			mRet = KtCustomer.filter({"customerId": data['customerId']}, raw=['firstName', 'lastName'], limit=1)
		elif isinstance(data['customerId'], list):
			mRet = {
				d['customerId']: {"firstName": d['firstName'], "lastName": d['lastName']}
				for d in KtCustomer.filter({"customerId": data['customerId']}, raw=['customerId', 'firstName', 'lastName'])
			}
		else:
			return Services.Response(error=(1001, [('customerId', 'invalid')]))

		# Return the result
		return Services.Response(mRet)

	def customerNote_create(self, data, sesh):
		"""Customer Note Create

		Creates a new note associated with the customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['action', 'content', 'customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "memo_notes",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# If the note is an SMS
		if data['action'] == 'Send Communication':
			return Services.Response(error=(1001, [('action', 'invalid')]))

		# Create base note data
		dNote = {
			"action": data['action'],
			"createdBy": sesh['memo_id'],
			"note": data['content'],
			"createdAt": sDT,
			"updatedAt": sDT
		}

		# If we got a label
		if 'label' in data:

			# If we have no order
			if 'orderId' not in data:
				return Services.Response(error=(1001, [('orderId', 'missing')]))

			# Figure out the role based on the label
			lLabel = data['label'].split(' - ')
			if lLabel[0] == 'Provider':
				lLabel[0] = 'Doctor'

			# Find the latest status for this order
			oStatus = SmpOrderStatus.filter(
				{"orderId": data['orderId']},
				limit=1
			)

			# If there's none
			if not oStatus:

				# Figure out the action
				if lLabel[0] == 'CSR':
					sAction = 'Send to CSR'
				elif lLabel[0] == 'Doctor':
					sAction = 'Send to Provider'
				else:
					sAction = 'Set Label'

				# Create a new status
				oStatus = SmpOrderStatus({
					"orderId": data['orderId'],
					"orderStatus": '',
					"reviewStatus": '',
					"attentionRole": lLabel[0] != '' and lLabel[0] or None,
					"orderLabel": len(lLabel) == 2 and data['label'] or '',
					"declineReason": None,
					"smpNoteId": None,
					"hrtProviderReviewOrderFlag": 'N',
					"currentFlag": 'Y',
					"labResultOnNoteFlag": 'N',
					"createdBy": 11,
					"modifiedBy": 11,
					"createdAt": sDT,
					"updatedAt": sDT
				});
				oStatus.create()

			# Else
			else:

				# Figure out the action
				if lLabel[0] == 'CSR' and oStatus['attentionRole'] != 'CSR':
					sAction = 'Send to CSR'
				elif lLabel[0] == 'Doctor' and oStatus['attentionRole'] != 'Doctor':
					sAction = 'Send to Provider'
				else:
					sAction = 'Set Label'

				# Update the existing status
				oStatus['attentionRole'] = lLabel[0] != '' and lLabel[0] or None
				oStatus['orderLabel'] = len(lLabel) == 2 and data['label'] or ''
				oStatus['updatedAt']: sDT
				oStatus.save()

			# Set the note to an order
			dNote['action'] = sAction
			dNote['parentTable'] = 'kt_order'
			dNote['parentColumn'] = 'orderId'
			dNote['columnValue'] = str(data['orderId'])

		# Else, use the customerId
		else:
			dNote['parentTable'] = 'kt_customer'
			dNote['parentColumn'] = 'customerId'
			dNote['columnValue'] = str(data['customerId'])

		# Attempt to create an instance to verify the fields
		try:
			oSmpNote = SmpNote(dNote)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the record and return the result
		return Services.Response(
			oSmpNote.create()
		)

	def customerNotes_read(self, data, sesh):
		"""Customer Notes

		Fetches all notes associated with the customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "memo_notes",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Convert ID to int
		try: data['customerId'] = int(data['customerId'])
		except ValueError: return Services.Response(error=(1001, [('customerId', "invalid")]))

		# Fetch all notes
		lNotes = SmpNote.byCustomer(data['customerId'])

		# Fetch the latest order status
		dStatus = SmpOrderStatus.latest(data['customerId'])

		# If we got a status
		if dStatus:

			# If the label is blank
			if dStatus['orderLabel'] in [None, '']:

				# If we have an attention role
				if dStatus['attentionRole']:
					dStatus['orderLabel'] = dStatus['attentionRole'] == 'Doctor' and 'Provider' or dStatus['attentionRole']

				# Else, make sure it's an empty string
				else:
					dStatus['orderLabel'] = ''

			# Set just the useful info
			dStatus = {
				"orderId": dStatus['orderId'],
				"label": dStatus['orderLabel']
			}

		# Fetch and return all notes
		return Services.Response({
			"notes": lNotes,
			"status": dStatus
		})

	def customerSearch_read(self, data, sesh):
		"""Customer Search

		Fetch and return a list of customers based on search data

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['filter'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If the filter isn't a dict
		if not isinstance(data['filter'], dict):
			return Services.Response(error=(1001, [('filter', "must be a key:value store")]))

		# If fields is not a list
		if 'fields' in data and not isinstance(data['fields'], list):
			return Services.Response(error=(1001, [('fields', "must be a list")]))

		# Search based on the data passed
		lRecords = KtCustomer.search(data['filter'], raw=('fields' in data and data['fields'] or True))

		# Get a list of all PENDING orders associated with the customers found
		lOrders = KtOrder.pendingByCustomers([
			d['customerId'] for d in lRecords
		])

		# Create a dictionary of customer ID to orders
		dOrders = {}
		for d in lOrders:
			if d['customerId'] not in dOrders:
				dOrders[d['customerId']] = []
			dOrders[d['customerId']].append(d)

		# Go through each record and add an orders list
		for d in lRecords:
			d['orders'] = d['customerId'] in dOrders and dOrders[d['customerId']] or False

		# Return the results
		return Services.Response(lRecords)

	def customerShipping_read(self, data, sesh):
		"""Customer Shipping

		Fetches all shipping (tracking code) associated with the customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Get all the records for the customer
		lCodes = ShippingInfo.filter(
			{"customerId": data['customerId']},
			raw=['code', 'type', 'date'],
			orderby=[['date', 'desc']]
		)

		# Go through and add the link
		for d in lCodes:
			try: d['link'] = self._TRACKING_LINKS[d['type']] % d['code']
			except KeyError: d['link'] = None

		# Return the records
		return Services.Response(lCodes)

	def customerStop_create(self, data, sesh):
		"""Customer Stop Create

		Adds a STOP flag on the specific phone number and service

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber', 'service'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Try to create an instance with the given data
		try:
			data['agent'] = sesh['memo_id']
			oStop = SMSStop(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Try to add it to the DB
		try:
			oStop.create()

			# Get current date/time
			sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

			# Track the change
			oStopChange = SMSStopChange({
				"phoneNumber": data['phoneNumber'],
				"action": 'add',
				"service": data['service'],
				"agent": sesh['memo_id'],
				"createdAt": sDT,
				"updatedAt": sDT
			})
			oStopChange.create()

			# Return OK
			return Services.Response(True)

		except Record_MySQL.DuplicateException as e:
			return Services.Response(error=1101)

	def customerStop_delete(self, data, sesh):
		"""Customer Stop Create

		Removes a STOP flag on the specific phone number and service

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber', 'service'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the flag
		oStop = SMSStop.filter({
			"phoneNumber": data['phoneNumber'],
			"service": data['service']
		}, limit=1)

		# If it doesn't exist
		if not oStop:
			return Services.Response(False)

		# If it exists but there's no agent
		if oStop['agent'] is None:
			return Services.Response(error=1509)

		# Delete the record
		oStop.delete()

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Track the change
		oStopChange = SMSStopChange({
			"phoneNumber": data['phoneNumber'],
			"action": 'remove',
			"service": data['service'],
			"agent": sesh['memo_id'],
			"createdAt": sDT,
			"updatedAt": sDT
		})
		oStopChange.create()

		# Return OK
		return Services.Response(True)

	def customerStops_read(self, data, sesh):
		"""Customer Stops

		Returns the list of STOP flags for all services associated with the
		phone number

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Fetch all flags for the number and return them
		return Services.Response({
			d['service']: d['agent'] for d in
			SMSStop.filter({
				"phoneNumber": data['phoneNumber']
			}, raw=['service', 'agent'])
		})

	def customerTransfer_update(self, data, sesh):
		"""Customer Transfer

		Transfers a customer from an agent to a provider

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_claims",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber', 'note'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the claim
		oClaim = CustomerClaimed.get(data['phoneNumber'])
		if not oClaim:
			return Services.Response(error=(1104, 'claim'))

		# If the owner of the claim isn't the one transferring
		if oClaim['user'] != sesh['memo_id']:
			return Services.Response(error=1513)

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# If there's a provider and an order ID
		if oClaim['provider'] and oClaim['orderId']:

			# Get the extra claim details
			dDetails = KtOrder.claimDetails(oClaim['orderId'])
			if not dDetails:
				return Services.Response(error=(1104, 'order'))

			# Generate the data for the record and the WS message
			dData = {
				"customerId": dDetails['customerId'],
				"orderId": oClaim['orderId'],
				"continuous": oClaim['continuous'],
				"user": oClaim['provider'],
				"transferredBy": sesh['memo_id'],
				"viewed": False
			}

			# Create a new claim instance for the agent and store in the DB
			oOrderClaim = KtOrderClaim(dData)

			# Add the extra details
			dData['customerName'] = dDetails['customerName']
			dData['type'] = dDetails['type']

			# Create the record in the DB
			try:
				if not oOrderClaim.create():
					return Services.Response(error=1100)

				# Sync the transfer for anyone interested
				Sync.push('monolith', 'user-%s' % str(oClaim['provider']), {
					"type": 'claim_transfered',
					"claim": dData
				})

			# If there's somehow a claim already
			except Record_MySQL.DuplicateException as e:

				# Find the existing claim
				oOldClaim = KtOrderClaim.get(dDetails['customerId'])

				# Save instead of create
				oOrderClaim.save()

				# Notify the old provider they lost the claim
				Sync.push('monolith', 'user-%s' % str(oOldClaim['user']), {
					"type": 'claim_removed',
					"customerId": dDetails['customerId']
				})

				# Notify the new provider they gained a claim
				Sync.push('monolith', 'user-%s' % str(oClaim['provider']), {
					"type": 'claim_transfered',
					"claim": dData
				})

			# Find the order status (fuck this is fucking stupid as fuck, fuck memo)
			oStatus = SmpOrderStatus.filter({
				"orderId": oOrderClaim['orderId']
			}, limit=1)
			if oStatus:
				oStatus['modifiedBy'] = sesh['memo_id']
				oStatus['attentionRole'] = 'Doctor'
				oStatus['orderLabel'] = 'Provider - Agent Transfer'
				oStatus['updatedAt'] = sDT
				oStatus.save()

		# Store transfer note
		oSmpNote = SmpNote({
			"action": 'Agent Transfer',
			"createdBy": sesh['memo_id'],
			"note": data['note'],
			"parentTable": 'kt_order',
			"parentColumn": 'orderId',
			"columnValue": oClaim['orderId'],
			"createdAt": sDT,
			"updatedAt": sDT
		})
		oSmpNote.create()

		# Return OK
		return Services.Response(True)

	def encounter_read(self, data):
		"""Encounter

		Returns encounter type based on state

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['state'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look up the state
		dState = SmpState.filter({
			"abbreviation": data['state']
		}, raw=['legalEncounterType'], limit=1)
		if not dState:
			return Services.Response(error=1104)

		# Return the encounter
		return Services.Response(dState['legalEncounterType'])

	def messageIncoming_create(self, data):
		"""Message Incoming

		Adds a new message from a customer

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'customerPhone', 'recvPhone', 'content'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Try to find a customer name
		dCustomer = KtCustomer.filter(
			{"phoneNumber": [data['customerPhone'], '1%s' % data['customerPhone']]},
			raw=['firstName', 'lastName'],
			orderby=[('updatedAt', 'DESC')],
			limit=1
		)

		# If we have one
		mName = dCustomer and \
				'%s %s' % (dCustomer['firstName'], dCustomer['lastName']) or \
				None

		# Validate values by creating an instance
		try:
			oCustomerCommunication = CustomerCommunication({
				"type": "Incoming",
				"fromName": mName,
				"fromPhone": data['customerPhone'][-10:],
				"toPhone": data['recvPhone'][-10:],
				"notes": data['content'],
				"createdAt": sDT,
				"updatedAt": sDT
			})
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Store the message record
		oCustomerCommunication.create()

		# Update the conversations
		iCount = CustomerMsgPhone.add(
			CustomerMsgPhone.INCOMING,
			data['customerPhone'],
			sDT,
			'\n--------\nReceived at %s\n%s\n' % (
				sDT,
				data['content']
			)
		)

		# If no conversation was updated
		if not iCount:

			oMsgPhone = CustomerMsgPhone({
				"customerPhone": data['customerPhone'],
				"customerName": mName,
				"lastMsg": '\n--------\nReceived at %s\n%s\n' % (
					sDT,
					data['content']
				),
				"lastMsgDir": 'Incoming',
				"lastMsgAt": sDT,
				"hiddenFlag": 'N',
				"totalIncoming": 1,
				"totalOutGoing": 0,
				"createdAt": sDT,
				"updatedAt": sDT
			})
			oMsgPhone.create()

		# Return OK
		return Services.Response(True)

	def messageOutgoing_create(self, data, sesh=None):
		"""Message Outgoing

		Sends a message to the customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If we have no session and no key
		if not sesh and '_internal_' not in data:
			return Services.Response(error=(1001, [('_internal_', 'missing')]))

		# Verify fields
		try: DictHelper.eval(data, ['customerPhone', 'content', 'type'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Check the number isn't blocked
		if SMSStop.filter({"phoneNumber": data['customerPhone'], "service": data['type']}):
			return Services.Response(error=1500)

		# If the content is too long
		if len(data['content']) >= 1600:
			return Services.Response(error=1510)

		# If it's internal
		if '_internal_' in data:

			# Verify the key, remove it if it's ok
			if not Services.internalKey(data['_internal_']):
				return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
			del data['_internal_']

			# If we don't have the name
			if 'name' not in data:
				return Services.Response(error=(1001, [('name', 'missing')]))

		# Else, verify the user and use their name
		else:

			# Make sure the user has the proper permission to do this
			oResponse = Services.read('auth', 'rights/verify', {
				"name": "csr_messaging",
				"right": Rights.CREATE
			}, sesh)
			if not oResponse.data:
				return Services.Response(error=Rights.INVALID)

			dUser = User.get(sesh['memo_id'], raw=['firstName', 'lastName'])
			data['name'] = '%s %s' % (dUser['firstName'], dUser['lastName'])

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Validate values by creating an instance
		try:
			oCustomerCommunication = CustomerCommunication({
				"type": "Outgoing",
				"fromName": data['name'],
				"toPhone": data['customerPhone'],
				"notes": data['content'],
				"createdAt": sDT,
				"updatedAt": sDT
			})
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Send the SMS
		oResponse = Services.create('communications', 'sms', {
			"_internal_": Services.internalKey(),
			"to": data['customerPhone'],
			"content": data['content'],
			"service": data['type']
		})

		# If we got an error
		if oResponse.errorExists():
			return oResponse

		# Store the message record
		oCustomerCommunication['sid'] = oResponse.data
		oCustomerCommunication.create()

		# Catch issues with summary
		try:

			# Update the conversations
			CustomerMsgPhone.add(
				CustomerMsgPhone.OUTGOING,
				data['customerPhone'],
				sDT,
				'\n--------\nSent by %s at %s\n%s\n' % (
					data['name'],
					sDT,
					data['content']
				)
			)

		# Catch any exceptions with summaries
		except Exception as e:
			try:
				# Email the error
				oResponse = Services.create('communications', 'email', {
					"_internal_": Services.internalKey(),
					"html_body": "Phone: %s\nContent: %s\nErrors: %s" % (
						data['customerPhone'],
						data['content'],
						', '.join([str(s) for s in e.args])
					),
					"subject": "MeMS: Summary Update Failed",
					"to": Conf.get(("developer", "emails")),
				})
			except:
				pass

			# Return OK but with a warning
			return Services.Response(True, warning="Message sent to customer, but Memo summary failed to update")

		# Return the ID of the new message
		return Services.Response(oCustomerCommunication['id'])

	def msgsClaimed_read(self, data, sesh):
		"""Messages: Claimed

		Fetches the list of phone numbers and name associated that the
		user has claimed

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Get the claimed records
		lClaimed = CustomerMsgPhone.claimed(sesh['memo_id'])

		# If there's no claimed, return
		if not lClaimed:
			return Services.Response([])

		# Get the phone numbers out of them
		lNumbers = []
		for d in lClaimed:
			lNumbers.append(d['customerPhone'])
			lNumbers.append('1%s' % d['customerPhone'])

		# Look up the customer IDs by phone number
		lCustomers = KtCustomer.filter(
			{"phoneNumber": lNumbers},
			raw=['customerId', 'phoneNumber'],
			orderby=[('updatedAt', 'ASC')],
		)

		# Create a map of customers by phone number
		dCustomers = {}
		for d in lCustomers:
			dCustomers[d['phoneNumber'][-10:]] = d['customerId']

		# Go through each claimed and associate the correct customer ID
		for d in lClaimed:
			d['customerId'] = d['customerPhone'] in dCustomers and \
								dCustomers[d['customerPhone']] or \
								0

		# Return the data
		return Services.Response(lClaimed)

	def msgsClaimedNew_read(self, data, sesh):
		"""Messages Claimed New

		Checks if there's any new messages in the given conversations

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['numbers'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If it's not a list
		if not isinstance(data['numbers'], (list,tuple)):
			return Services.Response(error=(1001, [('numbers', 'invalid')]))

		# Fetch the last claimed time
		iTS = CustomerClaimedLast.get(sesh['memo_id'])

		# Store the new time
		CustomerClaimedLast.set(sesh['memo_id'], int(time()))

		# Fetch and return the list of numbers with new messages
		return Services.Response(
			CustomerCommunication.newMessages(data['numbers'], iTS)
		)

	def msgsSearch_read(self, data, sesh):
		"""Messages: Search

		Searchs the message summaries and returns whatever's found

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Must search at least one
		if 'phone' not in data and \
			'name' not in data and \
			'content' not in data:
			return Services.Response(error=(1001, [('content', 'missing')]))

		# Fetch and return the data
		return Services.Response(
			CustomerMsgPhone.search(data)
		)

	def msgsSearchCustomer_read(self, data, sesh):
		"""Messages: Search Customer

		Searchs for a customer matching the values, then finds the associated
		conversation

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Must search at least one
		if 'id' not in data and \
			'email' not in data:
			return Services.Response(error=(1001, [('id', 'missing')]))

		# Figure out what to filter by
		dFilter = {}
		if 'id' in data: dFilter['customerId'] = data['id']
		if 'email' in data: dFilter['emailAddress'] = data['email']

		# Try to find the customer
		dCustomer = KtCustomer.filter(
			dFilter,
			raw=['phoneNumber'],
			orderby=[['updatedAt', 'DESC']],
			limit=1
		)

		# If there's no customer
		if not dCustomer:
			return Services.Response([])

		# Fetch and return the data based on the phone number
		return Services.Response(
			CustomerMsgPhone.search({"phone": dCustomer['phoneNumber']})
		)

	def msgsStatus_read(self, data, sesh):
		"""Messages: Status

		Get the status of a sent messages

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['ids'])
		except ValueError as e: return Services.Response(error=(1001, [(f, "missing") for f in e.args]))

		# If there's nothing
		if not data['ids']:
			return Services.Response([])

		# Get the status and error message of a specific message and return it
		return Services.Response(
			CustomerCommunication.get(data['ids'], raw=['id', 'status', 'errorMessage'])
		)

	def msgsUnclaimed_read(self, data, sesh):
		"""Messages: Unclaimed

		Fetches all summaries with incoming messages that have not been hidden
		or already claimed by a rep

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# If the order wasn't passed
		if 'order' not in data:
			data['order'] = 'ASC'

		# If the order is wrong
		if data['order'] not in ['ASC', 'DESC']:
			return Services.Response(error=(1001, [('order', 'invalid')]))

		# Fetch and return the data
		return Services.Response(
			CustomerMsgPhone.unclaimed(data['order'])
		)

	def msgsUnclaimedCount_read(self, data, sesh):
		"""Messages: Unclaimed Count

		Fetches the count of all summaries with incoming messages that have not
		been hidden or already claimed by a rep

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Fetch and return the data
		return Services.Response(
			CustomerMsgPhone.unclaimedCount()
		)

	def notesNew_read(self, data, sesh):
		"""Notes New

		Checks if there's any new notes for the given customers

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerIds'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If it's not a list
		if not isinstance(data['customerIds'], (list,tuple)):
			return Services.Response(error=(1001, [('customerIds', 'invalid')]))

		# If the ignore flag is set
		if 'ignore' in data:
			try: data['ignore'] = int(data['ignore'])
			except ValueError: return Services.Response(error=(1001, [('ignore', 'invalid')]))
		else:
			data['ignore'] = None

		# Fetch the last claimed time
		iTS = KtOrderClaimLast.get(sesh['memo_id'])

		# Store the new time
		KtOrderClaimLast.set(sesh['memo_id'], int(time()))

		# Fetch and return the list of customerIds with new messages
		return Services.Response(
			SmpNote.newNotes(data['customerIds'], iTS, data['ignore'])
		)

	def orderApprove_update(self, data, sesh):
		"""Order Approve

		Handles requests related to approving an order

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['orderId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Send the request to Konnektive
		oResponse = Services.update('konnektive', 'order/qa', {
			"action": 'APPROVE',
			"orderId": data['orderId']
		}, sesh)
		if oResponse.errorExists(): return oResponse

		# Find the order and change the status
		oKtOrder = KtOrder.filter({
			"orderId": data['orderId']
		}, limit=1)
		oKtOrder['orderStatus'] = 'COMPLETE'
		oKtOrder.save()

		# Update memo cause it sucks
		self.orderRefresh_update({
			"orderId": data['orderId']
		}, sesh)

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Store SOAP notes
		oSmpNote = SmpNote({
			"parentTable": 'kt_order',
			"parentColumn": 'orderId',
			"columnValue": data['orderId'],
			"action": 'Approve Order',
			"createdBy": sesh['memo_id'],
			"note": data['soap'],
			"createdAt": sDT,
			"updatedAt": sDT
		})
		oSmpNote.create()

		# Find the order status (fuck this is fucking stupid as fuck, fuck memo)
		oStatus = SmpOrderStatus.filter({
			"orderId": data['orderId']
		}, limit=1)
		if oStatus:
			oStatus['approvalProviderId'] = sesh['memo_id']
			oStatus['modifiedBy'] = sesh['memo_id']
			oStatus['attentionRole'] = None
			oStatus['orderLabel'] = None
			oStatus['orderStatus'] = 'COMPLETE'
			oStatus['reviewStatus'] = 'APPROVED'
			oStatus['updatedAt'] = sDT
			oStatus.save()

		# Notify the patient of the approval
		SMSWorkflow.providerApproves(data['orderId'], sesh['memo_id'], self)

		# Return OK
		return Services.Response(True)

	def orderClaim_create(self, data, sesh):
		"""Order Claim Create

		Stores a record to claim a PENDING order

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "order_claims",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'orderId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If 'continuous' is missing, assume false
		if 'continuous' not in data:
			data['continuous'] = False

		# Check how many claims this user already has
		iCount = KtOrderClaim.count(filter={
			"user": sesh['memo_id']
		})

		# If they're at or more than the maximum
		if iCount >= sesh['claims_max']:
			return Services.Response(error=1505)

		# Init warning
		mWarning = None

		# Attempt to create the record
		try:
			oKtOrderClaim = KtOrderClaim({
				"customerId": data['customerId'],
				"orderId": data['orderId'],
				"continuous": data['continuous'],
				"user": sesh['memo_id'],
				"viewed": True
			})
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Try to create the record
		try:
			oKtOrderClaim.create()

			# Send to SMSWorkflow
			SMSWorkflow.providerOpens(data['orderId'], sesh['memo_id'], self)

			# Add tracking
			oResponse = Services.create('providers', 'tracking', {
				"_internal_": Services.internalKey(),
				"action": 'viewed',
				"crm_type": 'knk',
				"crm_id": data['customerId']
			}, sesh)
			if oResponse.errorExists():
				mWarning = oResponse.error;

		# If we got a duplicate exception
		except Record_MySQL.DuplicateException:

			# Fine the user who claimed it
			dClaim = KtOrderClaim.get(data['customerId'], raw=['user']);

			# Return the error with the user ID
			return Services.Response(error=(1101, dClaim['user']))

		# Return OK
		return Services.Response(True, warning=mWarning)

	def orderClaim_delete(self, data, sesh):
		"""Order Claim Delete

		Deletes a record to claim a customer conversation by a order

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "order_claims",
			"right": Rights.DELETE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'reason'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Fetch the claim
		oClaim = KtOrderClaim.get(data['customerId'])
		if not oClaim:
			return Services.Response(error=1104)

		# If the user is not the one who made the claim
		if oClaim['user'] != sesh['memo_id']:
			return Services.Response(error=1000)

		# Init warning
		mWarning = None

		# If the order was approved
		if data['reason'] in ['approved', 'declined', 'transferred', 'x']:

			# Add tracking
			oResponse = Services.create('providers', 'tracking', {
				"_internal_": Services.internalKey(),
				"resolution": data['reason'],
				"crm_type": 'knk',
				"crm_id": data['customerId']
			}, sesh)
			if oResponse.errorExists():
				mWarning = oResponse.error;

		# Else, invalid reason
		else:
			return Services.Response(error=(1001, [('reason', 'invalid')]))

		# Attempt to delete the record and return the result
		return Services.Response(
			oClaim.delete(),
			warning=mWarning
		)

	def orderClaimView_update(self, data, sesh):
		"""Order Claim View

		Marks the claim as viewed for the first time

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "order_claims",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the claim
		oClaim = KtOrderClaim.get(data['customerId'])
		if not oClaim:
			return Services.Response(error=(1104, data['customerId']))

		# If the current owner of the claim is not the person clearing, return
		#	an error
		if oClaim['user'] != sesh['memo_id']:
			return Services.Response(error=1000)

		# Set the viewed flag
		oClaim['viewed'] = True
		oClaim.save()

		# Init warning
		mWarning = None

		# Add tracking
		oResponse = Services.create('providers', 'tracking', {
			"_internal_": Services.internalKey(),
			"action": 'viewed',
			"crm_type": 'knk',
			"crm_id": data['customerId']
		}, sesh)
		if oResponse.errorExists():
			mWarning = oResponse.error;

		# Return OK
		return Services.Response(True, warning=mWarning)

	def orderClaimed_read(self, data, sesh):
		"""Order Claimed

		Fetches the list of customers and name associated that the user has
		claimed

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "order_claims",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Get and return the claimed records
		return Services.Response(
			KtOrderClaim.byUser(sesh['memo_id'])
		)

	def orderContinuous_create(self, data, sesh):
		"""Order Continuous Create

		Creates a new continuous order using an existing KNK order ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Validate rights
		Rights.check(sesh, 'orders', Rights.CREATE)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'orderId', 'purchaseId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Try to create the instance
		try:
			oOC = KtOrderContinuous({
				"customerId": int(data['customerId']),
				"orderId": data['orderId'],
				"purchaseId": data['purchaseId'],
				"active": False,
				"status": 'PENDING'
			})
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Try to create the record and return the ID
		try:
			return Services.Response(
				oOC.create()
			)
		except Record_MySQL.DuplicateException:
			return Services.Error(1101)

	def orderContinuous_read(self, data, sesh):
		"""Order Continuous Read

		Returns the details of the continuous order using the base KNK order
		as a starting point

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Validate rights
		Rights.check(sesh, 'orders', Rights.READ)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'orderId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the local order
		dOrderCont = KtOrderContinuous.filter({
			"customerId": data['customerId'],
			"orderId": data['orderId']
		}, raw=['status'], limit=1)
		if not dOrderCont:
			return Services.Response(error=1104)

		# Find the order in Konnektive
		oResponse = Services.read('konnektive', 'order', {
			"orderId": data['orderId']
		}, sesh)
		if oResponse.errorExists():
			return oResponse

		# Store the order
		dOrder = oResponse.data

		# Overwrite the status
		dOrder['status'] = dOrderCont['status']

		# Return the order
		return Services.Response(dOrder)

	def orderContinuousApprove_update(self, data, sesh):
		"""Order Continuous Approve

		Updates the status of a continuous order to Approved

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Validate rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "orders",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'orderId', 'soap'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the order
		oOrder = KtOrderContinuous.filter({
			"customerId": data['customerId'],
			"orderId": data['orderId']
		}, limit=1)
		if not oOrder:
			return Services.Response(error=1104)

		# If the order is not pending
		if oOrder['status'] != 'PENDING':
			return Services.Response(error=1515)

		# Set the status and user, then save the order
		oOrder['status'] = 'COMPLETE'
		oOrder['user'] = sesh['memo_id']
		oOrder.save()

		# Notify the patient
		SMSWorkflow.providerApprovesContinuous(data['orderId'], sesh['memo_id'], self)

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Store SOAP notes
		oSmpNote = SmpNote({
			"parentTable": 'kt_customer',
			"parentColumn": 'customerId',
			"columnValue": str(data['customerId']),
			"action": 'Approve Continuous Order',
			"createdBy": sesh['memo_id'],
			"note": data['soap'],
			"createdAt": sDT,
			"updatedAt": sDT
		})
		oSmpNote.create()

		# Return OK
		return Services.Response(True)

	def orderContinuousDecline_update(self, data, sesh):
		"""Order Continuous Decline

		Updates the status of a continuous order to Declined

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Validate rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "orders",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'orderId', 'reason'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure customer ID is an int
		try: data['customerId'] = int(data['customerId'])
		except ValueError: return Services.Response(error=(1001, [('customerId', 'not an int')]))

		# Find the order
		oOrder = KtOrderContinuous.filter({
			"customerId": data['customerId'],
			"orderId": data['orderId']
		}, limit=1)
		if not oOrder:
			return Services.Response(error=1104)

		# If the order is not pending
		if oOrder['status'] != 'PENDING':
			return Services.Response(error=1515)

		# Cancel the purchase in Konnektive
		oResponse = Services.update('konnektive', 'purchase/cancel', {
			"purchaseId": oOrder['purchaseId'],
			"reason": data['reason']
		}, sesh)
		if oResponse.errorExists(): return oResponse

		# Set the status and user, then save the order
		oOrder['status'] = 'DECLINED'
		oOrder['user'] = sesh['memo_id']
		oOrder.save()

		# Notify the patient
		SMSWorkflow.providerDeclinesContinuous(data['orderId'], sesh['memo_id'], self)

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Store Decline note
		oSmpNote = SmpNote({
			"parentTable": 'kt_customer',
			"parentColumn": 'customerId',
			"columnValue": str(data['customerId']),
			"action": 'Decline Order',
			"createdBy": sesh['memo_id'],
			"note": self._DECLINE_NOTES[data['reason']],
			"createdAt": sDT,
			"updatedAt": sDT
		})
		oSmpNote.create()

		# Return OK
		return Services.Response(True)

	def orderDecline_update(self, data, sesh):
		"""Order Decline

		Handles requests related to declining an order

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['orderId', 'reason'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Check the reason
		if data['reason'] not in self._DECLINE_NOTES.keys():
			return Services.Response(error=(1001, [('reason', 'invalid')]))

		# Send the request to Konnektive
		oResponse = Services.update('konnektive', 'order/qa', {
			"action": 'DECLINE',
			"orderId": data['orderId']
		}, sesh)
		if oResponse.errorExists(): return oResponse

		# Find the order and change the status
		oKtOrder = KtOrder.filter({
			"orderId": data['orderId']
		}, limit=1)
		oKtOrder['orderStatus'] = 'DECLINED'
		oKtOrder.save()

		# Update memo cause it sucks
		self.orderRefresh_update({
			"orderId": data['orderId']
		}, sesh)

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Store Decline note
		oSmpNote = SmpNote({
			"parentTable": 'kt_order',
			"parentColumn": 'orderId',
			"columnValue": data['orderId'],
			"action": 'Decline Order',
			"createdBy": sesh['memo_id'],
			"note": self._DECLINE_NOTES[data['reason']],
			"createdAt": sDT,
			"updatedAt": sDT
		})
		oSmpNote.create()

		# Find the order status (fuck this is fucking stupid as fuck, fuck memo)
		oStatus = SmpOrderStatus.filter({
			"orderId": data['orderId']
		}, limit=1)
		if oStatus:
			oStatus['modifiedBy'] = sesh['memo_id']
			oStatus['attentionRole'] = None
			oStatus['orderLabel'] = None
			oStatus['orderStatus'] = 'DECLINED'
			oStatus['reviewStatus'] = 'DECLINED'
			oStatus['declineReason'] = '%s Decline' % data['reason']
			oStatus['updatedAt'] = sDT
			oStatus.save()

		# If it was a medical decline
		if data['reason'] == 'Medical':

			# Notify the patient of the decline
			SMSWorkflow.providerDeclines(data['orderId'], sesh['memo_id'], self)

		# Return OK
		return Services.Response(True)

	def orderLabel_update(self, data, sesh):
		"""Order Label

		Creates or updates the label associated with an order

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "memo_notes",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['orderId', 'label'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# If we got a label
		if 'label' in data:

			# If we have no label
			if 'orderId' not in data:
				return Services.Response(error=(1001, [('label', 'missing')]))

			# Figure out the role based on the label
			lLabel = data['label'].split(' - ')
			if lLabel[0] == 'Provider':
				lLabel[0] = 'Doctor'

			# Find the latest status for this order
			oStatus = SmpOrderStatus.filter(
				{"orderId": data['orderId']},
				limit=1
			)

			# If there's none
			if not oStatus:

				# Figure out the action
				if lLabel[0] == 'CSR':
					sAction = 'Send to CSR'
				elif lLabel[0] == 'Doctor':
					sAction = 'Send to Provider'
				else:
					sAction = 'Set Label'

				# Create a new status
				oStatus = SmpOrderStatus({
					"orderId": data['orderId'],
					"orderStatus": '',
					"reviewStatus": '',
					"attentionRole": lLabel[0] != '' and lLabel[0] or None,
					"orderLabel": len(lLabel) == 2 and data['label'] or '',
					"declineReason": None,
					"smpNoteId": None,
					"currentFlag": 'Y',
					"createdBy": 11,
					"modifiedBy": 11,
					"createdAt": sDT,
					"updatedAt": sDT
				});
				oStatus.create()

			# Else
			else:

				# Figure out the action
				if lLabel[0] == 'CSR' and oStatus['attentionRole'] != 'CSR':
					sAction = 'Send to CSR'
				elif lLabel[0] == 'Doctor' and oStatus['attentionRole'] != 'Doctor':
					sAction = 'Send to Provider'
				else:
					sAction = 'Set Label'

				# Update the existing status
				oStatus['attentionRole'] = lLabel[0] != '' and lLabel[0] or None
				oStatus['orderLabel'] = len(lLabel) == 2 and data['label'] or ''
				oStatus['updatedAt']: sDT
				oStatus.save()

	def orderRefresh_update(self, data, sesh):
		"""Order Refresh

		Welcome to the stupidity that is Memo

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['orderId'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make the request of Memo to refresh it's shitty data from KNK
		oRes = Memo.update('rest/order/refresh', {
			"orderId": data['orderId']
		})

		# If there's no error
		if 'error' in oRes and oRes['error'] is False:
			del oRes['error']

		# Return the response
		return Services.Response.fromDict(oRes)

	def orderTransfer_update(self, data, sesh):
		"""Order Transfer

		Sends an order to an agent

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "order_claims",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'agent', 'note'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the claim
		oOrderClaim = KtOrderClaim.get(data['customerId'])
		if not oOrderClaim:
			return Services.Response(error=1104)

		# If the owner of the claim isn't the one transferring
		if oOrderClaim['user'] != sesh['memo_id']:
			return Services.Response(error=1513)

		# If we don't have an agent
		bAgent = True
		if data['agent'] == 0:

			# We had no specific agent
			bAgent = False

			# Find the round robin
			oResponse = Services.read('providers', 'roundrobin', {}, sesh);
			if oResponse.errorExists(): return oResponse

			# If there's only one
			if len(oResponse.data) == 1:
				data['agent'] = oResponse.data[0]

			# Else, get the counts and use the one with the least
			else:
				lCounts = CustomerClaimed.counts(oResponse.data)
				data['agent'] = lCounts[0]['user']

		# Find the order associated with the claim
		dKtOrder = KtOrder.filter({
			"orderId": oOrderClaim['orderId']
		}, raw=['phoneNumber'], limit=1)
		if not dKtOrder:
			return Services.Response(error=1104)

		# Generate the data for the record and the WS message
		dData = {
			"phoneNumber": dKtOrder['phoneNumber'],
			"user": data['agent'],
			"transferredBy": sesh['memo_id'],
			"provider": sesh['memo_id'],
			"orderId": oOrderClaim['orderId'],
			"continuous": oOrderClaim['continuous'],
			"viewed": False
		}

		# Create a new claim instance for the agent and store in the DB
		oCustClaim = CustomerClaimed(dData)
		try:
			if not oCustClaim.create():
				return Services.Response(error=1100)

			# Sync the transfer for anyone interested
			Sync.push('monolith', 'user-%s' % str(data['agent']), {
				"type": 'claim_transfered',
				"claim": dData
			})

		except Record_MySQL.DuplicateException as e:

			# Find the existing claim
			dOldClaim = CustomerClaimed.get(dKtOrder['phoneNumber'], raw=['user'])

			# If we had a specific agent requested
			if bAgent or dOldClaim['user'] == data['agent']:

				# Save instead of create
				oCustClaim.save()

				# Notify the old agent they lost the claim
				Sync.push('monolith', 'user-%s' % str(dOldClaim['user']), {
					"type": 'claim_removed',
					"phoneNumber": dKtOrder['phoneNumber']
				})

				# Notify the new agent they gained a claim
				Sync.push('monolith', 'user-%s' % str(data['agent']), {
					"type": 'claim_transfered',
					"claim": dData
				})

			# Else, we don't care who the agent is
			else:

				# Keep the existing agent and save
				oCustClaim['agent'] = dOldClaim['user']
				oCustClaim.save()

				# Notify the agent the claim has been update
				dData['agent'] = dOldClaim['user']
				Sync.push('monolith', 'user-%s' % str(dOldClaim['user']), {
					"type": 'claim_updated',
					"claim": dData
				})

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Find the order status (fuck this is fucking stupid as fuck, fuck memo)
		oStatus = SmpOrderStatus.filter({
			"orderId": oOrderClaim['orderId']
		}, limit=1)
		if oStatus:
			oStatus['modifiedBy'] = sesh['memo_id']
			oStatus['attentionRole'] = 'CSR'
			oStatus['orderLabel'] = 'CSR - Provider Transfer'
			oStatus['updatedAt'] = sDT
			oStatus.save()

		# Store transfer note
		oSmpNote = SmpNote({
			"action": 'Provider Transfer',
			"createdBy": sesh['memo_id'],
			"note": data['note'],
			"parentTable": 'kt_order',
			"parentColumn": 'orderId',
			"columnValue": oOrderClaim['orderId'],
			"createdAt": sDT,
			"updatedAt": sDT
		})
		oSmpNote.create()

		# See if we have a customer msg summary
		dCMP = CustomerMsgPhone.existsByCustomerId(data['customerId'])
		if not dCMP['id']:

			# Get current time
			sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

			# Create a new convo
			oConvo = CustomerMsgPhone({
				"customerPhone": dCMP['customerPhone'],
				"customerName": dCMP['customerName'],
				"lastMsgAt": sDT,
				"hiddenFlag": 'N',
				"totalIncoming": 0,
				"totalOutGoing": 0,
				"createdAt": sDT,
				"updatedAt": sDT
			})
			oConvo.create()

		# Return OK
		return Services.Response(True)

	def ordersPendingCsr_read(self, data, sesh):
		"""Order Pending CSR

		Returns the unclaimed orders set to the CSR role

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch and return the unclaimed CSR orders
		return Services.Response(
			KtOrder.queueCsr()
		)

	def ordersPendingCsrCount_read(self, data, sesh):
		"""Orders Pending CSR Count

		Returns the count of unclaimed orders to to the CSR role

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Fetch and return the data
		return Services.Response(
			KtOrder.queueCsrCount()
		)

	def ordersPendingProviderEd_read(self, data, sesh):
		"""Order Pending Provider ED

		Returns the unclaimed pending ED orders

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If the user has no ED states
		if not sesh['states']['ed']:
			return Services.Response(error=1506)

		# Fetch and return the queue
		return Services.Response(
			KtOrder.queue('ed', sesh['states']['ed'])
		)

	def ordersPendingProviderEdCont_read(self, data, sesh):
		"""Order Pending Provider ED

		Returns the unclaimed pending ED orders

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If the user has no ED states
		if not sesh['states']['ed']:
			return Services.Response(error=1506)

		# Fetch and return the queue
		return Services.Response(
			KtOrderContinuous.queue('ed', sesh['states']['ed'])
		)

	def ordersPendingProviderHrt_read(self, data, sesh):
		"""Order Pending Provider HRT

		Returns the unclaimed pending HRT orders

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If the user has no HRT states
		if not sesh['states']['hrt']:
			return Services.Response(error=1506)

		# Fetch and return the queue
		return Services.Response(
			KtOrder.queue('hrt', sesh['states']['hrt'])
		)

	def ordersPendingProviderHrtCont_read(self, data, sesh):
		"""Order Pending Provider HRT

		Returns the unclaimed pending HRT orders

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If the user has no HRT states
		if not sesh['states']['hrt']:
			return Services.Response(error=1506)

		# Fetch and return the queue
		return Services.Response(
			KtOrderContinuous.queue('hrt', sesh['states']['hrt'])
		)

	def passwdForgot_create(self, data):
		"""Password Forgot (Generate)

		Creates the key that will be used to allow a user to change their
		password if they forgot it

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'url'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the user by email
		dUser = User.filter({"email": data['email']}, raw=['id'], limit=1)
		if not dUser:
			return Services.Response(False)

		# Look for a forgot record by user id
		oForgot = Forgot.get(dUser['id'])

		# Is there already a key in the user?
		if oForgot and 'regenerate' not in data:

			# Is it not expired?
			if oForgot['expires'] > int(time()):
				return Services.Response(True)

		# Upsert the forgot record with a timestamp (for expiry) and the key
		sKey = StrHelper.random(32, '_0x')
		oForgot = Forgot({
			"user": dUser['id'],
			"expires": int(time()) + Conf.get(("services", "auth", "forgot_expire"), 600),
			"key": sKey
		})
		if not oForgot.create(conflict="replace"):
			return Services.Response(error=1100)

		# Forgot email template variables
		dTpl = {
			"key": sKey,
			"url": "%s%s" % (
				data['url'],
				sKey
			)
		}

		# Email the user the key
		oResponse = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/forgot.html', dTpl, dUser['locale']),
			"subject": Templates.generate('email/forgot_subject.txt', {}, dUser['locale']),
			"to": data['email'],
		})
		if oResponse.errorExists():
			return oResponse

		# Return OK
		return Services.Response(True)

	def passwdForgot_update(self, data):
		"""Password Forgot (Change Password)

		Validates the key and changes the password to the given value

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['passwd', 'key'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the forgot by the key
		oForgot = Forgot.filter({"key": data['key']}, limit=1)
		if not oForgot:
			return Services.Response(error=1203) # Don't let people know if the key exists or not

		# Check if the key has expired
		if oForgot['expires'] <= int(time()):
			return Services.Response(error=1203)

		# Make sure the new password is strong enough
		if not User.passwordStrength(data['passwd']):
			return Services.Response(error=1204)

		# Find the User
		oUser = User.get(oForgot['user'])
		if not oUser:
			return Services.Response(error=1203)

		# Store the new password and update
		oUser['passwd'] = User.passwordHash(data['passwd'])
		oUser.save(changes=False)

		# Delete the forgot record
		oForgot.delete()

		# Return OK
		return Services.Response(True)

	def phoneChange_update(self, data, sesh):
		"""Phone Change

		Changes the phone number associated with a customer and all records
		associated with that number

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "customers",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['old', 'new'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Check the values are numeric and cut down to the last 10 digits
		for k in ['old', 'new']:
			if not data[k].isnumeric():
				return Services.Response(error=(1001, [(k, 'is not numeric')]))
			data[k] = data[k][-10:]

		# If we have a customer ID
		if 'customerId' in data:

			# Find the customer
			oCustomer = KtCustomer.filter({
				"customerId": data['customerId'],
				"phoneNumber": [data['old'], '1%s' % data['old']]
			}, limit=1)
			if not oCustomer:
				return Services.Response(error=1104)

			# Update the customer in Konnektive
			oResponse = Services.update('konnektive', 'customer', {
				"customerId": data['customerId'],
				"phone": data['new']
			}, sesh)
			if oResponse.errorExists():
				return oResponse

			# Sync the local copy
			oCustomer['phoneNumber'] = data['new']
			oCustomer.save()

		# Update all incoming messages
		CustomerCommunication.updateField('fromPhone', data['new'], filter={
			"fromPhone": data['old']
		})

		# Update all outgoing messages
		CustomerCommunication.updateField('toPhone', data['new'], filter={
			"toPhone": data['old']
		})

		# Find the old summary
		oOldSummary = CustomerMsgPhone.filter({
			"customerPhone": [data['old'], '1%s' % data['old']]
		}, limit=1)

		# Find the new summary
		oNewSummary = CustomerMsgPhone.filter({
			"customerPhone": [data['new'], '1%s' % data['new']]
		}, limit=1)

		# If we found one
		if oOldSummary or oNewSummary:

			# If we have both summaries
			if oOldSummary and oNewSummary:

				# Delete the old one
				oOldSummary.delete()

				# Set the new one to work on
				oSummary = oNewSummary

			# Else, choose from whichever we got
			else:
				oSummary = oNewSummary and oNewSummary or oOldSummary

			# Set the new number
			oSummary['customerPhone'] = data['new']

			# Get the conversations for the number
			lMsgs = CustomerCommunication.thread(data['new'])

			# If we got any messages
			if len(lMsgs):

				# Set the last message fields
				iLast = len(lMsgs) - 1;
				oSummary['lastMsgDir'] = lMsgs[iLast]['fromPhone'] == data['new'] and \
											'Incoming' or \
											'Outgoing'
				oSummary['lastMsgAt'] = lMsgs[iLast]['createdAt']

				# Keep track of incoming/outgoing and summary texts
				iIncoming = 0
				iOutgoing = 0
				lTexts = []

				# Go through each one in reverse
				for d in reversed(lMsgs):

					# If it's incoming
					if d['fromPhone'] == data['new']:
						iIncoming += 1
						lTexts.append('\n--------\nReceived at %s\n%s' % (
							d['createdAt'],
							d['notes']
						))

					# Else it's outgoing
					else:
						iOutgoing += 1
						lTexts.append('\n--------\nSent by %s at %s\n%s' % (
							d['fromName'],
							d['createdAt'],
							d['notes']
						))

				# Update the rest of the fields
				oSummary['totalIncoming'] = iIncoming
				oSummary['totalOutGoing'] = iOutgoing
				oSummary['lastMsg'] = ''.join(lTexts)
				oSummary['updatedAt'] = arrow.get().format('YYYY-MM-DD HH:mm:ss')

			# Save the summary
			oSummary.save()

		# Look for a claim associated with the number
		oClaim = CustomerClaimed.get(data['old'])
		if oClaim:

			# If the claim already exists
			if CustomerClaimed.exists(data['new']):

				# Notify the user they lost the claim
				Sync.push('monolith', 'user-%s' % str(oClaim['user']), {
					"type": 'claim_removed',
					"phoneNumber": oClaim['phoneNumber']
				})

				# Delete the claim
				oClaim.delete()

			# Else, swap it
			else:

				# Notify the user the claim is swapped
				Sync.push('monolith', 'user-%s' % str(oClaim['user']), {
					"type": 'claim_swapped',
					"phoneNumber": oClaim['phoneNumber'],
					"newNumber": data['new']
				})

				# Swap the number
				oClaim.swapNumber(data['new'])

		# Return OK
		return Services.Response(True)

	def providerCalendly_read(self, data, sesh):
		"""Provider Calendly

		Returns all upcoming appointments associated with the provider

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'calendly', Rights.READ)

		# Check for meme_id in session
		if 'memo_id' not in sesh:
			return Services.Response(error=1507)

		# If 'new_only' not passed, assume true
		if 'new_only' not in data:
			data['new_only'] = True

		# Get the emails for the user
		dUser = User.get(sesh['memo_id'], raw=['email', 'calendlyEmail'])
		if not dUser:
			return Services.Response(error=(1104, 'user'))

		# Find all calendly appointments in progress or in the future associated
		#	with the user
		lAppts = Calendly.byProvider(
			[dUser['email'], dUser['calendlyEmail']],
			data['new_only']
		)

		print(lAppts)

		# Return anything found
		return Services.Response(lAppts)

	def providerSms_create(self, data, sesh):
		"""Provider SMS

		Sends an SMS from a provider to a customer and stores it in the notes

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "memo_notes",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId', 'content'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If the content is too long
		if len(data['content']) >= 1600:
			return Services.Response(error=1510)

		# Find the name of the creator
		dUser = User.get(sesh['memo_id'], raw=['firstName', 'lastName'])
		if not dUser:
			return Services.Response(error=(1104, 'user'))

		# Find the name and phone number of the customer
		dKtCustomer = KtCustomer.filter({
			"customerId": str(data['customerId'])
		}, raw=['shipFirstName', 'shipLastName', 'phoneNumber'], limit=1)
		if not dKtCustomer:
			return Services.Response(error=(1104, 'customer'))

		# Check the number isn't blocked
		if SMSStop.filter({"phoneNumber": dKtCustomer['phoneNumber'], "service": 'doctor'}):
			return Services.Response(error=1500)

		# Send the SMS
		oResponse = Services.create('communications', 'sms', {
			"_internal_": Services.internalKey(),
			"to": dKtCustomer['phoneNumber'][-10:],
			"content": data['content'],
			"service": 'doctor'
		})

		# If we got an error
		if oResponse.errorExists():
			return oResponse

		# Monolith is stupid af and saving SMS messages in the same table as
		#	notes is a special level of laziness and/or incompetence
		data['content'] = '\n[Sender] %s %s\n[Receiver] %s %s - %s\n[Content] %s' % (
			dUser['firstName'],
			dUser['lastName'],
			dKtCustomer['shipFirstName'],
			dKtCustomer['shipLastName'],
			dKtCustomer['phoneNumber'],
			data['content']
		)

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Create an instance to check fields
		try:
			oSmpNote = SmpNote({
				"parentTable": 'kt_customer',
				"parentColumn": 'customerId',
				"columnValue": str(data['customerId']),
				"action": 'Send Communication',
				"createdBy": sesh['memo_id'],
				"note": data['content'],
				"createdAt": sDT,
				"updatedAt": sDT
			})
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Save the record
		oSmpNote.create()

		# Pass the info along to SMS workflow if we have an order ID
		if 'orderId' in data:
			SMSWorkflow.providerMessaged(data['orderId'], oSmpNote['id'])

		# Return the ID of the new note
		return Services.Response(oSmpNote['id'])

	def providers_read(self, data, sesh):
		"""Providers

		Returns a map of user ID to name of only Doctor users

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Fetch all users with Doctor userRole and concat their name
		return Services.Response([
			{"id": d['id'], "name": '%s %s' % (d['firstName'], d['lastName'])}
			for d in User.filter({
				"userRole": 'Doctor',
				"activeFlag": 'Y'
			}, raw=['id', 'firstName', 'lastName'], orderby=['firstName', 'lastName'])
		])

	def signin_create(self, data):
		"""Signin

		Used to verify a user sign in, but doesn't actually create the session.
		Can only be called by other services

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'userName', 'passwd'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Look for the user by alias
		oUser = User.filter({"userName": data['userName']}, limit=1)
		if not oUser:
			return Services.Response(error=1201)

		# If the user is not active
		if oUser['activeFlag'] == 'N':
			return Services.Response(error=1503)

		# Validate the password
		if not bcrypt.checkpw(data['passwd'].encode('utf8'), oUser['password'].encode('utf8')):
			return Services.Response(error=1201)

		# Return the record data
		return Services.Response(oUser.record())

	def statsClaimed_read(self, data, sesh):
		"""Stats: Claimed

		Fetchs the number of claims made by users

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_stats",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch and return claim stats
		return Services.Response(
			CustomerClaimed.stats()
		)

	def user_create(self, data, sesh):
		"""User Create

		Creates a new user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'userName', 'firstName', 'lastName', 'password'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Check if a user with that user name already exists
		if User.exists(data['userName'], 'userName'):
			return Services.Response(error=1501)

		# Check the password strength
		if not User.passwordStrength(data['password']):
			return Services.Response(error=1502)

		# Hash the password
		data['password'] = bcrypt.hashpw(data['password'].encode('utf8'), bcrypt.gensalt()).decode('utf8')

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Add defaults
		if 'userRole' not in data: data['userRole'] = 'CSR'
		data['createdAt'] = sDT
		data['updatedAt'] = sDT

		# Validate by creating a Record instance
		try:
			oUser = User(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the row and return the result
		return Services.Response(
			oUser.create()
		)

	def user_read(self, data, sesh):
		"""User Read

		Fetches the logged in user and returns their data

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Fetch it from the DB
		dUser = User.get(sesh['memo_id'], raw=True)

		# If it doesn't exist
		if not dUser:
			return Services.Response(error=1104)

		# Remove the passwd
		del dUser['password']

		# Fetch the permissions
		oResponse = Services.read('auth', 'permissions/self', {}, sesh)
		if oResponse.errorExists(): return oResponse

		# Add the permissions to the dict
		dUser['permissions'] = oResponse.dataExists() and oResponse.data or {}

		# Return the user data
		return Services.Response(dUser)

	def user_update(self, data, sesh):
		"""User Update

		Updates the logged in user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# If the user is not the one logged in
		if 'id' in data and ('memo_id' not in data or data['id'] != sesh['memo_id'] or '_internal_' in data):

			# If there's no internal
			if '_internal_' not in data:
				return Services.Response(error=(1001, [('_internal_', 'missing')]))

			# Verify the key, remove it if it's ok
			if not Services.internalKey(data['_internal_']):
				return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
			del data['_internal_']

			# Find the User
			oUser = User.get(data['id'])
			if not oUser:
				return Services.Response(error=1104)

			# Remove the ID from the data
			del data['id']

		# Else get the logged in user
		else:

			# Fetch it from the cache
			oUser = User.get(sesh['memo_id'])

		# Remove fields that can't be changed
		if 'password' in data: del data['passwd']

		# If the username was changed
		if 'userName' in data:

			# Check if a user with that user name already exists
			if User.exists(data['userName'], 'userName'):
				return Services.Response(error=1501)

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oUser[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# Update the updatedAt
		oUser['updatedAt'] = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# If there was any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Response(
			oUser.save()
		)

	def userActive_update(self, data, sesh):
		"""User Active

		Updates the active flag on a user to true (Y) or false (N)

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'id', 'active'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Find the User
		oUser = User.get(data['id'])
		if not oUser:
			return Services.Response(error=1104)

		# Set the new state of the active flag
		oUser['activeFlag'] = data['active'] and 'Y' or 'N'

		# Update the updatedAt time to now
		oUser['updatedAt'] = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Save and return the result
		return Services.Response(
			oUser.save()
		)

	def userId_read(self, data):
		"""User ID

		Fetches the ID of a user based on one or multiple fields in the User
		table

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Get the user
		dUser = User.filter(data, raw=['id'], limit=1)

		# If there's no user
		if not dUser:
			return Services.Response(False)

		# Return the user's ID
		return Services.Response(dUser['id'])

	def userName_read(self, data, sesh):
		"""User Name

		Fetchs one or more names based on IDs, returns as a dictionary (one ID)
		or of ID to name (multiple IDs)

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# If there's only one
		if isinstance(data['id'], int):
			mRet = User.get(data['id'], raw=['firstName', 'lastName'])
		elif isinstance(data['id'], list):
			mRet = {
				d['id']: {"firstName": d['firstName'], "lastName": d['lastName']}
				for d in User.get(data['id'], raw=['id', 'firstName', 'lastName'])
			}
		else:
			return Services.Response(error=(1104, [('id', 'invalid')]))

		# Return the result
		return Services.Response(mRet)

	def userPasswd_update(self, data, sesh):
		"""User Password

		Changes the password for the current signed in user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# If it's an internal request
		if '_internal_' in data:

			# Verify fields
			try: DictHelper.eval(data, ['user_id', 'passwd'])
			except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

			bInternal = True
			sUserId = data['user_id']
			sPasswd = data['passwd']

		# Else, it must be someone updating their own
		else:

			# Verify fields
			try: DictHelper.eval(data, ['passwd', 'new_passwd'])
			except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

			bInternal = False
			sUserId = sesh['memo_id']
			sPasswd = data['new_passwd']

		# Find the user
		oUser = User.get(sUserId)
		if not oUser:
			return Services.Response(error=1104)

		# Validate the password if necessary
		if not bInternal:
			if not bcrypt.checkpw(data['passwd'].encode('utf8'), oUser['password'].encode('utf8')):
				return Services.Response(error=(1001, [('passwd', 'invalid')]))

		# Make sure the new password is strong enough
		if not User.passwordStrength(sPasswd):
			return Services.Response(error=1204)

		# Set the new password and save
		oUser['password'] = bcrypt.hashpw(sPasswd.encode('utf8'), bcrypt.gensalt()).decode('utf8')
		oUser['updatedAt'] = arrow.get().format('YYYY-MM-DD HH:mm:ss')
		oUser.save()

		# Return OK
		return Services.Response(True)

	def users_read(self, data, sesh):
		"""Users

		Returns users by ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, "missing") for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# If there's no IDs
		if not data['id']:
			return Services.Response(error=(1001, [('id', 'empty')]))

		# If the fields aren't passed
		if 'fields' not in data:
			data['fields'] = True

		# Fetch and return the users
		return Services.Response(
			User.get(data['id'], raw=data['fields'])
		)

	def workflow_create(self, data):
		"""Workflow

		Works as a passthrough for SMS Workflow requests

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'call', 'args'])
		except ValueError as e: return Services.Response(error=(1001, [(f, "missing") for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Try to find the module method or else return an error
		try:
			fMethod = getattr(SMSWorkflow, data['call'])
		except Exception as e:
			return Services.Response(error=(1511, str(e)))

		# Try to call the method with the passed arguments
		try:
			data['monolith'] = self
			bRes = fMethod(**data['args'])
		except Exception as e:
			return Services.Response(error=(1512, str(e)))

		# Return the response
		return Services.Response(bRes)
