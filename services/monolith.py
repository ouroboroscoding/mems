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
from shared import Rights, Sync

# Records imports
from records.monolith import \
	Calendly, Campaign, CustomerClaimed, CustomerClaimedLast, CustomerCommunication, \
	CustomerMsgPhone, DsPatient, Forgot, HrtLabResultTests, KtCustomer, KtOrder, \
	KtOrderClaim, ShippingInfo, SmpNote, SmpOrderStatus, SMSStop, TfAnswer, \
	TfLanding, TfQuestion, TfQuestionOption, User, \
	init as recInit

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

# mip forms
_mipForms = ['MIP-H1', 'MIP-A2', 'MIP-A1']

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
				"totalOutgoing": 0,
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
				"provider": data['provider']
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
			return Services.Response(error=1000)

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
					"transferredBy": sesh['memo_id']
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

	def customerClaimClear_update(self, data, sesh):
		"""Customer Claim Clear

		Clears the transferred by state

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

		# Clear the transferred by
		oClaim['transferredBy'] = None
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
			dCustomer['phoneNumber']
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
			{"customerId": data['customerId']},
			raw=['patientId'],
			limit=1
		)

		# If there's no patient
		if not dPatient:
			return Services.Response(0)

		# Return the ID
		return Services.Response(dPatient['patientId'])

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

	def customerMip_read(self, data, sesh):
		"""Customer MIP

		Gets the latest MIP by a form type or types

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
		try: DictHelper.eval(data, ['customerId', 'form'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If we want any form
		if data['form'] == 'any':
			data['form'] = None

		# Find the customer by ID
		dCustomer = KtCustomer.filter(
			{"customerId": data['customerId']},
			raw=['lastName', 'emailAddress', 'phoneNumber'],
			limit=1
		)

		# Get the latest landing by type
		dLanding = TfLanding.latest(
			dCustomer['lastName'],
			dCustomer['emailAddress'] or '',
			dCustomer['phoneNumber'],
			data['form']
		)

		# If there's no mip
		if not dLanding:
			return Services.Response(0)

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

		# Return the MIP
		return Services.Response(dData)

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
			dCustomer['phoneNumber']
		)

		# If there's no mip
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

		# If it's not found
		if not oTfAnswer:
			return Services.Response(error=1104)

		# Update the value
		try:
			oTfAnswer['value'] = data['value']
		except ValueError as e:
			return Services.Response(error=(1001, [e.args[0]]))

		# Save the record and return the result
		return Services.Response(
			oTfAnswer.save()
		)

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
		try: DictHelper.eval(data, ['content', 'action'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# We must have either a customer ID or order ID
		if 'customer_id' not in data and 'order_id' not in data:
			return Services.Response(error=(1001, [('customer_id', 'missing'), ('order_id', 'missing')]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "memo_notes",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# If we got a customer ID
		if 'customer_id' in data:

			# Attempt to create the record
			try:
				oSmpNote = SmpNote({
					"parentTable": 'kt_customer',
					"parentColumn": 'customerId',
					"columnValue": str(data['customer_id']),
					"action": data['action'],
					"createdBy": sesh['memo_id'],
					"note": data['content'],
					"createdAt": sDT,
					"updatedAt": sDT
				})
			except ValueError as e:
				return Services.Response(error=(1001, e.args[0]))

		# Else we got an order ID
		else:

			# If we have no label
			if 'label' not in data:
				return Services.Response(error=(1001, [('label', 'missing')]))

			# Figure out the role based on the label
			lLabel = data['label'].split(' - ')
			if lLabel[0] == 'Provider':
				lLabel[0] = 'Doctor'

			# Find the latest status for this order
			oStatus = SmpOrderStatus.filter(
				{"orderId": data['order_id']},
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
					"orderId": data['order_id'],
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

			# Attempt to create the record
			try:
				oSmpNote = SmpNote({
					"parentTable": 'kt_order',
					"parentColumn": 'orderId',
					"columnValue": data['order_id'],
					"action": sAction,
					"createdBy": sesh['memo_id'],
					"note": data['content'],
					"createdAt": sDT,
					"updatedAt": sDT
				})
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
			return Services.Response(
				oStop.create()
			)
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

		# Else, delete it and return the response
		return Services.Response(
			oStop.delete()
		)

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

	def messageIncoming_create(self, data):
		"""Message Incoming

		Adds a new message from a customer

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'customerPhone', 'recvPhone', 'content', 'type'])
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
		CustomerMsgPhone.addIncoming(
			data['customerPhone'],
			sDT,
			'\n--------\nReceived at %s\n%s\n' % (
				sDT,
				data['content']
			)
		)

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

		# If it's internal
		if '_internal_' in data:

			# Verify the key, remove it if it's ok
			if not Services.internalKey(data['_internal_']):
				return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
			del data['_internal_']

			# If we don't have the name
			if 'name' not in data:
				return Services.Response(error=(1001, [('name', 'missing')]))

		# Else, verify the user and user their name
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
			CustomerMsgPhone.addOutgoing(
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

		print(time())

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

		# Check how many claims this user already has
		iCount = KtOrderClaim.count(filter={
			"user": sesh['memo_id']
		})

		# If they're at or more than the maximum
		if iCount >= sesh['claims_max']:
			return Services.Response(error=1505)

		# Attempt to create the record
		try:
			oKtOrderClaim = KtOrderClaim({
				"customerId": data['customerId'],
				"orderId": data['orderId'],
				"user": sesh['memo_id']
			})
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Try to create the record
		try:
			oKtOrderClaim.create()

			# Return OK
			return Services.Response(True)

		# If we got a duplicate exception
		except Record_MySQL.DuplicateException:

			# Fine the user who claimed it
			dClaim = KtOrderClaim.get(data['customerId'], raw=['user']);

			# Return the error with the user ID
			return Services.Response(error=(1101, dClaim['user']))

		# Else, we failed to create the record
		return Services.Response(False)

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

		# If the order was approved
		if data['reason'] == 'approve':
			pass

		# If the order was rejected
		elif data['reason'] == 'rejected':
			pass

		# If the order was transfered
		elif data['reason'] == 'to_csr':
			pass

		# Else, invalid reason
		else:
			return Services.Response(error=(1001, [('reason', 'invalid')]))

		# Attempt to delete the record and return the result
		return Services.Response(
			oClaim.delete()
		)

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
			KtOrder.claimed(sesh['memo_id'])
		)

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
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "calendly",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Check for meme_id in session
		if 'memo_id' not in sesh:
			return Services.Response(error=1507)

		# Get the emails for the user
		dUser = User.get(sesh['memo_id'], raw=['email', 'calendlyEmail'])
		if not dUser:
			return Services.Response(error=(1104, 'user'))

		# Find all calendly appointments in progress or in the future associated
		#	with the user
		lAppts = Calendly.filter({
			"prov_emailAddress": [dUser['email'], dUser['calendlyEmail']],
			"end": {"gte": Record_MySQL.Literal('CURRENT_TIMESTAMP')}
		}, orderby='start', raw=True)

		# Return anything found
		return Services.Response(lAppts)

	def signin_create(self, data):
		"""Signin

		Used to verify a user sign in, but doesn't actually create the session.
		Can only be called by other services

		Arguments
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
			CustomerClaim.stats()
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
