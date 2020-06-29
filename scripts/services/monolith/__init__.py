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
import uuid

# Pip imports
import arrow
import bcrypt
from redis import StrictRedis
from RestOC import Conf, DictHelper, Errors, Services, \
					Sesh, StrHelper, Templates

# Service imports
from .records import CustomerClaimed, CustomerCommunication, CustomerMsgPhone, \
						DsPatient, Forgot, KtCustomer, KtOrder, ShippingInfo, \
						SmpNote, SmpOrderStatus, SMSStop, TfAnswer, TfLanding, \
						TfQuestion, TfQuestionOption, User, WdOutreach, \
						WdTrigger, \
						init as recInit

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

# mip forms
_mipForms = ['MIP-H1', 'MIP-A2', 'MIP-A1']

class Monolith(Services.Service):
	"""Monolith Service class

	Service for Monolith, sign in, sign up, etc.
	"""

	_install = [CustomerClaimed, Forgot]
	"""Record types called in install"""

	_TRACKING_LINKS = {
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

	def customerClaim_create(self, data, sesh):
		"""Customer Claim Create

		Stores a record to claim a customer conversation for a user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

				# Verify fields
		try: DictHelper.eval(data, ['phoneNumber'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Attempt to create the record
		try:
			oCustomerClaimed = CustomerClaimed({
				"phoneNumber": data['phoneNumber'],
				"user": sesh['user_id']
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record
		if oCustomerClaimed.create(conflict='replace'):

			# Find the customer associated
			dCustomer = KtCustomer.filter(
				{"phoneNumber": [data['phoneNumber'], '1%s' % data['phoneNumber']]},
				raw=['customerId'],
				orderby=[('updatedAt', 'DESC')],
				limit=1
			)

			# Return the ID and phone
			return Services.Effect({
				"customerId": dCustomer['customerId'],
				"customerPhone": data['phoneNumber']
			})

		# Else, we failed to create the record
		return Services.Effect(False)

	def customerClaim_delete(self, data, sesh):
		"""Customer Claim Delete

		Deletes a record to claim a customer conversation by a user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Attempt to delete the record
		CustomerClaimed.deleteGet(data['phoneNumber'])

		# Return OK
		return Services.Effect(True)

	def customerClaim_update(self, data, sesh):
		"""Customer Claim Update

		Switches a claim to another agent

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber', 'user_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Find the claim
		oClaim = CustomerClaimed.get(data['phoneNumber'])
		if not oClaim:
			return Services.Effect(error=(1104, data['phoneNumber']))

		# Find the user
		if not User.exists(data['user_id']):
			return Services.Effect(error=(1104, data['user_id']))

		# Switch the user associated with the claim
		oClaim['user'] = data['user_id']
		oClaim.save()

		# Return OK
		return Services.Effect(True)

	def customerDsid_read(self, data, sesh):
		"""Customer DoseSpot ID

		Returns the ID of the DoseSpote patient based on their customer ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Find the patient ID
		dPatient = DsPatient.filter(
			{"customerId": data['customerId']},
			raw=['patientId'],
			limit=1
		)

		# If there's no patient
		if not dPatient:
			return Services.Effect(0)

		# Return the ID
		return Services.Effect(dPatient['patientId'])

	def customerIdByPhone_read(self, data, sesh):
		"""Customer Hide

		Marks a customer conversation as hidden

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['phoneNumber'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the latest customer with the given number
		dCustomer = KtCustomer.filter(
			{"phoneNumber": [data['phoneNumber'], '1%s' % data['phoneNumber']]},
			raw=['customerId'],
			orderby=[('updatedAt', 'DESC')],
			limit=1
		)

		# If there's no customer
		if not dCustomer:
			return Services.Effect(0)

		# Return the ID
		return Services.Effect(dCustomer['customerId'])

	def customerHide_update(self, data, sesh):
		"""Customer Hide

		Marks a customer conversation as hidden

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerPhone'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Update the records hidden field
		CustomerMsgPhone.updateField('hiddenFlag', 'Y', filter={"customerPhone": data['customerPhone']})

		# Return OK
		return Services.Effect(True)

	def customerMessages_read(self, data, sesh):
		"""Customer Messages

		Fetches all messages associated with a customer (phone number)

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerPhone'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Get the messages
		lMsgs = CustomerCommunication.thread(data['customerPhone'])

		# Get the type
		sType = len(KtOrder.ordersByPhone(data['customerPhone'])) and 'support' or 'sales'

		# Find out if the user is blocked anywhere
		bStop = SMSStop.filter({"phoneNumber": data['customerPhone'], "service": sType}) and True or False

		# Fetch and return all the messages associated with the number
		return Services.Effect({
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
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Attempt to find the customer by phone number
		dCustomer = KtCustomer.filter(
			{"customerId": data['customerId']},
			raw=['lastName', 'emailAddress', 'phoneNumber'],
			orderby=[('dateUpdated', 'DESC')],
			limit=1
		)

		# Try to find the landing
		lLandings = TfLanding.find(
			dCustomer['lastName'],
			dCustomer['emailAddress'],
			dCustomer['phoneNumber']
		)

		# If there's no mip
		if not lLandings:
			return Services.Effect(0)

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
		return Services.Effect(lRet)

	def customerMipAnswer_update(self, data, sesh):
		"""Customer MIP Answer Update

		Updates the answer to a single MIP question

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['landing_id', 'ref', 'value'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Find the answer
		oTfAnswer = TfAnswer.filter({
			"landing_id": data['landing_id'],
			"ref": data['ref']
		}, limit=1)

		# If it's not found
		if not oTfAnswer:
			return Services.Effect(error=1104)

		# Update the value
		try:
			oTfAnswer['value'] = data['value']
		except ValueError as e:
			return Services.Effect(error=(1001, [e.args[0]]))

		# Save the record and return the result
		return Services.Effect(
			oTfAnswer.save()
		)

	def customerNote_create(self, data, sesh):
		"""Customer Note Create

		Creates a new note associated with the customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['content', 'action'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# We must have either a customer ID or order ID
		if 'customer_id' not in data and 'order_id' not in data:
			return Services.Effect(error=(1001, [('customer_id', 'missing'), ('order_id', 'missing')]))

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# If we got a customer ID
		if 'customer_id' in data:

			# Attempt to create the record
			try:
				oSmpNote = SmpNote({
					"parentTable": 'kt_customer',
					"parentColumn": 'customerId',
					"columnValue": data['customer_id'],
					"action": data['action'],
					"createdBy": sesh['user_id'],
					"note": data['content'],
					"createdAt": sDT,
					"updatedAt": sDT
				})
			except ValueError as e:
				return Services.Effect(error=(1001, e.args[0]))

		# Else we got an order ID
		else:

			# If we have no label
			if 'label' not in data:
				return Services.Effect(error=(1001, [('label', 'missing')]))

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
					"orderLabel": data['label'],
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
				oStatus['orderLabel'] = data['label']
				oStatus['updatedAt']: sDT
				oStatus.save()

			# Attempt to create the record
			try:
				oSmpNote = SmpNote({
					"parentTable": 'kt_order',
					"parentColumn": 'orderId',
					"columnValue": data['order_id'],
					"action": sAction,
					"createdBy": sesh['user_id'],
					"note": data['content'],
					"createdAt": sDT,
					"updatedAt": sDT
				})
			except ValueError as e:
				return Services.Effect(error=(1001, e.args[0]))

		# Create the record and return the result
		return Services.Effect(
			oSmpNote.create()
		)

	def customerNotes_read(self, data, sesh):
		"""Customer Notes

		Fetches all notes associated with the customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Convert ID to int
		try: data['customerId'] = int(data['customerId'])
		except ValueError: return Services.Effect(error=(1001, [('customerId', "invalid")]))

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
		return Services.Effect({
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
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

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
		return Services.Effect(lCodes)

	def customerTriggerInfo_read(self, data, sesh):
		"""Customer Trigger Info

		Returns the last trigger associated with the customer, including any
		possible outreach and eligibility

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		#oEff = self.verify_read({
		#	"name": "prescriptions",
		#	"right": Rights.READ
		#}, sesh)
		#if not oEff.data:
		#	return Services.Effect(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['customerId'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for a trigger with any possible outreach and eligibility
		dTrigger = WdTrigger.withOutreachEligibility(data['customerId'])

		# If there's nothing
		if not dTrigger:
			dTrigger = 0

		# Return
		return Services.Effect(dTrigger)

	def messageIncoming_create(self, data):
		"""Message Incoming

		Adds a new message from a customer

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'customerPhone', 'recvPhone', 'content', 'type'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Effect(error=Errors.SERVICE_INTERNAL_KEY)
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
			return Services.Effect(error=(1001, e.args[0]))

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
		return Services.Effect(True)

	def messageOutgoing_create(self, data, sesh):
		"""Message Outgoing

		Sends a message to the customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['customerPhone', 'content', 'type'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Check the number isn't blocked
		if SMSStop.filter({"phoneNumber": data['customerPhone'], "service": data['type']}):
			return Services.Effect(error=1500)

		# Get the user's name
		dUser = User.get(sesh['user_id'], raw=['firstName', 'lastName'])
		sName = '%s %s' % (dUser['firstName'], dUser['lastName'])

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Validate values by creating an instance
		try:
			oCustomerCommunication = CustomerCommunication({
				"type": "Outgoing",
				"fromName": sName,
				"toPhone": data['customerPhone'],
				"notes": data['content'],
				"createdAt": sDT,
				"updatedAt": sDT
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Send the SMS
		oEff = Services.create('communications', 'sms', {
			"_internal_": Services.internalKey(),
			"to": data['customerPhone'],
			"content": data['content'],
			"service": data['type']
		})

		# If we got an error
		if oEff.errorExists():
			return oEff

		# Store the message record
		oCustomerCommunication.create()

		# Update the conversations
		CustomerMsgPhone.addOutgoing(
			data['customerPhone'],
			sDT,
			'\n--------\nSent by %s at %s\n%s\n' % (
				sName,
				sDT,
				data['content']
			)
		)

		# Return OK
		return Services.Effect(True)

	def msgsClaimed_read(self, data, sesh):
		"""Messages: Claimed

		Fetches the list of phone numbers and name associated that the
		user has claimed

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Store the current time in the session
		sesh['claimed_last'] = time();
		sesh.save()

		# Get the claimed records
		lClaimed = CustomerMsgPhone.claimed(sesh['user_id'])

		# If there's no claimed, return
		if not lClaimed:
			return Services.Effect([])

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
		return Services.Effect(lClaimed)

	def msgsClaimedNew_read(self, data, sesh):
		"""Messages Claimed New

		Checks if there's any new messages in the given conversations

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['numbers'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# If it's not a list
		if not isinstance(data['numbers'], (list,tuple)):
			return Services.Effect(error=(1001, [('numbers', 'invalid')]))

		# Fetch the last claimed time
		iTS = sesh['claimed_last']

		# Store the new time
		sesh['claimed_last'] = time();
		sesh.save()

		# Fetch and return the list of numbers with new messages
		return Services.Effect(
			CustomerCommunication.newMessages(data['numbers'], iTS)
		)

	def msgsSearch_read(self, data, sesh):
		"""Messages: Search

		Searchs the message summaries and returns whatever's found

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Must search at least one
		if 'phone' not in data and \
			'name' not in data and \
			'content' not in data:
			return Services.Effect(error=(1001, [('content', 'missing')]))

		# Fetch and return the data
		return Services.Effect(
			CustomerMsgPhone.search(data)
		)

	def msgsUnclaimed_read(self, data, sesh):
		"""Messages: Unclaimed

		Fetches all summaries with incoming messages that have not been hidden
		or already claimed by a rep

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Fetch and return the data
		return Services.Effect(
			CustomerMsgPhone.unclaimed()
		)

	def passwdForgot_create(self, data):
		"""Password Forgot (Generate)

		Creates the key that will be used to allow a user to change their
		password if they forgot it

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'url'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the user by email
		dUser = User.filter({"email": data['email']}, raw=['id'], limit=1)
		if not dUser:
			return Services.Effect(False)

		# Look for a forgot record by user id
		oForgot = Forgot.get(dUser['id'])

		# Is there already a key in the user?
		if oForgot and 'regenerate' not in data:

			# Is it not expired?
			if oForgot['expires'] > int(time()):
				return Services.Effect(True)

		# Upsert the forgot record with a timestamp (for expiry) and the key
		sKey = StrHelper.random(32, '_0x')
		oForgot = Forgot({
			"user": dUser['id'],
			"expires": int(time()) + Conf.get(("services", "auth", "forgot_expire"), 600),
			"key": sKey
		})
		if not oForgot.create(conflict="replace"):
			return Services.Effect(error=1100)

		# Forgot email template variables
		dTpl = {
			"key": sKey,
			"url": "%s%s" % (
				data['url'],
				sKey
			)
		}

		# Email the user the key
		oEffect = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/forgot.html', dTpl, dUser['locale']),
			"subject": Templates.generate('email/forgot_subject.txt', {}, dUser['locale']),
			"to": data['email'],
		})
		if oEffect.errorExists():
			return oEffect

		# Return OK
		return Services.Effect(True)

	def passwdForgot_update(self, data):
		"""Password Forgot (Change Password)

		Validates the key and changes the password to the given value

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['passwd', 'key'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the forgot by the key
		oForgot = Forgot.filter({"key": data['key']}, limit=1)
		if not oForgot:
			return Services.Effect(error=1203) # Don't let people know if the key exists or not

		# Check if the key has expired
		if oForgot['expires'] <= int(time()):
			return Services.Effect(error=1203)

		# Make sure the new password is strong enough
		if not User.passwordStrength(data['passwd']):
			return Services.Effect(error=1204)

		# Find the User
		oUser = User.get(oForgot['user'])
		if not oUser:
			return Services.Effect(error=1203)

		# Store the new password and update
		oUser['passwd'] = User.passwordHash(data['passwd'])
		oUser.save(changes=False)

		# Delete the forgot record
		oForgot.delete()

		# Return OK
		return Services.Effect(True)

	def session_read(self, data, sesh):
		"""Session

		Returns the ID of the user logged into the current session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return Services.Effect({
			"user" : {
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
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the user by alias
		oUser = User.filter({"userName": data['userName']}, limit=1)
		if not oUser:
			return Services.Effect(error=1201)

		# Validate the password
		if not bcrypt.checkpw(data['passwd'].encode('utf8'), oUser['password'].encode('utf8')):
			return Services.Effect(error=1201)

		# Create a new session
		oSesh = Sesh.create("mono:" + uuid.uuid4().hex)

		# Store the user ID and information in it
		oSesh['user_id'] = oUser['id']

		# Save the session
		oSesh.save()

		# Return the session ID and primary user data
		return Services.Effect({
			"session": oSesh.id(),
			"user": {
				"id": oSesh['user_id']
			}
		})

	def signout_create(self, data, sesh):
		"""Signout

		Called to sign out a user and destroy their session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Effect
		"""

		# Close the session so it can no longer be found/used
		sesh.close()

		# Return OK
		return Services.Effect(True)

	def user_read(self, data, sesh):
		"""User Read

		Fetches the logged in user and returns their data

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Effect
		"""

		# Fetch it from the DB
		dUser = User.get(sesh['user_id'], raw=True)

		# If it doesn't exist
		if not dUser:
			return Services.Effect(error=1104)

		# Remove the passwd
		del dUser['password']

		# Return the user data
		return Services.Effect(dUser)

	def user_update(self, data, sesh):
		"""User Update

		Updates the logged in user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Effect
		"""

		# Fetch it from the cache
		oUser = User.get(sesh['user_id'])

		# Remove fields that can't be changed
		del data['_id']
		if 'password' in data: del data['passwd']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oUser[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Effect(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Effect(
			oUser.save(changes={"user": sesh['user_id']})
		)

	def userName_read(self, data, sesh):
		"""User Name

		Fetchs one or more names based on IDs, returns as a dictionary of ID to
		name

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Return the dictionary of IDs to names
		return Services.Effect({
			d['id']: {"firstName": d['firstName'], "lastName": d['lastName']}
			for d in User.get(data['id'], raw=['id', 'firstName', 'lastName'])
		})

	def userPasswd_update(self, data, sesh):
		"""User Password

		Changes the password for the current signed in user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['passwd', 'new_passwd'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Find the user
		oUser = User.get(sesh['user_id'])
		if not oUser:
			return Services.Effect(error=1104)

		# Validate the password
		if not bcrypt.checkpw(data['passwd'].encode('utf8'), oUser['password'].encode('utf8')):
			return Services.Effect(error=(1001, [('passwd', 'invalid')]))

		# Make sure the new password is strong enough
		if not User.passwordStrength(data['new_passwd']):
			return Services.Effect(error=1204)

		# Set the new password and save
		oUser['password'] = bcrypt.hashpw(data['new_passwd'].encode('utf8'), bcrypt.gensalt()).decode('utf8')
		print(oUser['password'])
		oUser.save()

		# Return OK
		return Services.Effect(True)
