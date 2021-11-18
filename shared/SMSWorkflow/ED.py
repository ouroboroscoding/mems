# coding=utf8
"""ED Workflow

Handles finding the correct customer, generating the template, and sending
off the SMS
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-09-01"

# Python imports
import traceback

# Pip imports
from RestOC import Services

# Cron imports
from crons import emailError

# Record imports
from records.monolith import KtOrder, SMSPatientWorkflow, User

# Shared imports
from shared import Shipping

# Local imports
from . import fetchTemplate, processTemplate, GROUP_ED

# ED Step values
STEP_ED_KONNEKTIVE_CANCELED		= 0
STEP_ED_CARD_RECEIVED			= 1
STEP_ED_ONE_DAY_NOTICE			= 2
STEP_ED_PROVIDER_OPENS			= 3
STEP_ED_PROVIDER_DECLINE		= 4
STEP_ED_PROVIDER_PRE_APPROVES	= 5
STEP_ED_PROVIDER_APPROVES		= 6
STEP_ED_PROVIDER_MESSAGED		= 7
STEP_ED_PATIENT_RESPONDED		= 8
STEP_ED_ORDER_ARCHIVED			= 9
STEP_ED_ORDER_CANCELED			= 10
STEP_ED_MEETING_SET				= 11
STEP_ED_LEAD					= 12
STEP_ED_LEAD_NO_ORDER_24		= 13
STEP_ED_LEAD_NO_ORDER_48		= 14
STEP_ED_CONTINUOUS_APPROVES		= 15
STEP_ED_CONTINUOUS_DECLINE		= 16

# Non step value
PACKAGE_SHIPPED				= 50
WELCOME						= 51

def providerApproves(order_id, user_id, monolith):
	"""Provider Approves

	Called when the provider who claimed the order approves that order

	Arguments:
		order_id (str): The ID of the order approved
		user_id (int): The ID of the user (provider)
		monolith (services.monolith.Monolith): An instance of the service used
			to send SMS messages

	Returns:
		bool
	"""

	# Find the order's workflow
	oWorkflow = SMSPatientWorkflow.filter({
		"orderId": order_id,
		"groupId": GROUP_ED
	}, limit=1);

	# If there's no order, assume it's an older customer and just return
	if not oWorkflow:
		return False

	# If the patient has already been send the approve message, do nothing
	if oWorkflow['step'] in [STEP_ED_KONNEKTIVE_CANCELED, STEP_ED_PROVIDER_APPROVES]:
		return False

	# Find the order
	dOrder = KtOrder.filter(
		{"orderId": order_id},
		raw=['firstName', 'lastName', 'emailAddress', 'phoneNumber', 'state'],
		limit=1
	)
	if not dOrder:
		return False

	# Find the user
	dUser = User.get(user_id, raw=['firstName', 'lastName'])
	if not dUser:
		return False

	# Get the template
	sContent = fetchTemplate(
		oWorkflow['groupId'],
		'async',
		STEP_ED_PROVIDER_APPROVES
	);

	# Process the template
	sContent = processTemplate(sContent, dOrder, {
		"provider_name": '%s %s' % (dUser['firstName'], dUser['lastName'])
	});

	# Message data
	dMsg = {
		"_internal_": Services.internalKey(),
		"name": "SMS Workflow",
		"customerPhone": dOrder['phoneNumber'],
		"content": sContent,
		"type": 'support'
	}

	# Send the SMS to the patient
	oResponse = monolith.messageOutgoing_create(dMsg)

	# If there's an error sending the SMS
	if oResponse.errorExists():
		emailError(
			'SMSWorkflow providerApproves Error',
			'Couldn\'t send sms:\n\n%s\n\n%s' % (
				str(dOrder),
				str(oResponse)
			)
		)
		return False

	# Update the workflow step
	oWorkflow['step'] = STEP_ED_PROVIDER_APPROVES
	oWorkflow['tries'] = 0
	oWorkflow.save()

	# Return OK
	return True

def providerApprovesContinuous(order_id, user_id, monolith):
	"""Provider Approves Continuous

	Called when the provider who claimed the continuous order approves it

	Arguments:
		order_id (str): The ID of the order approved
		user_id (int): The ID of the user (provider)
		monolith (services.monolith.Monolith): An instance of the service used
			to send SMS messages

	Returns:
		bool
	"""

	# Find the order
	dOrder = KtOrder.filter(
		{"orderId": order_id},
		raw=['firstName', 'lastName', 'emailAddress', 'phoneNumber', 'state'],
		limit=1
	)
	if not dOrder:
		return False

	# Find the user
	dUser = User.get(user_id, raw=['firstName', 'lastName'])
	if not dUser:
		return False

	# Get the template
	sContent = fetchTemplate(1, 'async', STEP_ED_CONTINUOUS_APPROVES);

	# Process the template
	sContent = processTemplate(sContent, dOrder, {
		"provider_name": '%s %s' % (dUser['firstName'], dUser['lastName'])
	});

	# Message data
	dMsg = {
		"_internal_": Services.internalKey(),
		"name": "SMS Workflow",
		"customerPhone": dOrder['phoneNumber'],
		"content": sContent,
		"type": 'support'
	}

	# Send the SMS to the patient
	oResponse = monolith.messageOutgoing_create(dMsg)

	# If there's an error sending the SMS
	if oResponse.errorExists():
		emailError(
			'SMSWorkflow providerApprovesContinuous Error',
			'Couldn\'t send sms:\n\n%s\n\n%s' % (
				str(dOrder),
				str(oResponse)
			)
		)
		return False

	# Return OK
	return True

def providerDeclines(order_id, user_id, monolith):
	"""Provider Declines

	Called when the provider who claimed the order declines that order

	Arguments:
		order_id (str): The ID of the order declined
		user_id (int): The ID of the user (provider)
		monolith (services.monolith.Monolith): An instance of the service used
			to send SMS messages

	Returns:
		bool
	"""

	# Find the order's workflow
	oWorkflow = SMSPatientWorkflow.filter({
		"orderId": order_id,
		"groupId": GROUP_ED
	}, limit=1);

	# If there's no order, assume it's an older customer and just return
	if not oWorkflow:
		return False

	# If the patient has already been send the approve message, do nothing
	if oWorkflow['step'] in [STEP_ED_KONNEKTIVE_CANCELED, STEP_ED_PROVIDER_DECLINE]:
		return False

	# Find the order
	dOrder = KtOrder.filter(
		{"orderId": order_id},
		raw=['firstName', 'lastName', 'emailAddress', 'phoneNumber', 'state'],
		limit=1
	)
	if not dOrder:
		return False

	# Find the user
	dUser = User.get(user_id, raw=['firstName', 'lastName'])
	if not dUser:
		return False

	# Get the template
	sContent = fetchTemplate(
		oWorkflow['groupId'],
		'async',
		STEP_ED_PROVIDER_DECLINE
	);

	# Process the template
	sContent = processTemplate(sContent, dOrder, {
		"provider_name": '%s %s' % (dUser['firstName'], dUser['lastName'])
	});

	# Message data
	dMsg = {
		"_internal_": Services.internalKey(),
		"name": "SMS Workflow",
		"customerPhone": dOrder['phoneNumber'],
		"content": sContent,
		"type": 'support'
	}

	# Send the SMS to the patient
	oResponse = monolith.messageOutgoing_create(dMsg)

	# If there's an error sending the SMS
	if oResponse.errorExists():
		emailError(
			'SMSWorkflow providerDeclines Error',
			'Couldn\'t send sms:\n\n%s\n\n%s' % (
				str(dOrder),
				str(oResponse)
			)
		)
		return False

	# Update the workflow step
	oWorkflow['step'] = STEP_ED_PROVIDER_DECLINE
	oWorkflow['tries'] = 0
	oWorkflow.save();

	# Return OK
	return True

def providerDeclinesContinuous(order_id, user_id, monolith):
	"""Provider Declines Continuous

	Called when the provider who claimed the continuous order declines it

	Arguments:
		order_id (str): The ID of the order declined
		user_id (int): The ID of the user (provider)
		monolith (services.monolith.Monolith): An instance of the service used
			to send SMS messages

	Returns:
		bool
	"""

	# Find the order
	dOrder = KtOrder.filter(
		{"orderId": order_id},
		raw=['firstName', 'lastName', 'emailAddress', 'phoneNumber', 'state'],
		limit=1
	)
	if not dOrder:
		return False

	# Find the user
	dUser = User.get(user_id, raw=['firstName', 'lastName'])
	if not dUser:
		return False

	# Get the template
	sContent = fetchTemplate(1, 'async', STEP_ED_CONTINUOUS_DECLINE);

	# Process the template
	sContent = processTemplate(sContent, dOrder, {
		"provider_name": '%s %s' % (dUser['firstName'], dUser['lastName'])
	});

	# Message data
	dMsg = {
		"_internal_": Services.internalKey(),
		"name": "SMS Workflow",
		"customerPhone": dOrder['phoneNumber'],
		"content": sContent,
		"type": 'support'
	}

	# Send the SMS to the patient
	oResponse = monolith.messageOutgoing_create(dMsg)

	# If there's an error sending the SMS
	if oResponse.errorExists():
		emailError(
			'SMSWorkflow providerDeclinesContinuous Error',
			'Couldn\'t send sms:\n\n%s\n\n%s' % (
				str(dOrder),
				str(oResponse)
			)
		)
		return False

	# Return OK
	return True

def providerMessaged(order_id, note_id):
	"""Provider Messages

	Called when the provider sends a message to the patient, usually for further
	information

	Arguments:
		order_id (str): The order associated with the message
		note_id (int): The ID of the note created by the message

	Returns:
		bool
	"""

	# Find the patient's workflow
	oWorkflow = SMSPatientWorkflow.filter({
		"orderId": order_id,
		"groupId": GROUP_ED
	}, limit=1);

	# If there's no patient, assume it's an older customer and just return
	if not oWorkflow:
		return False

	# If the order is already approved / denied / canceled, ignore this
	if oWorkflow['step'] in [STEP_ED_KONNEKTIVE_CANCELED, STEP_ED_PROVIDER_DECLINE, STEP_ED_PROVIDER_APPROVES, STEP_ED_ORDER_CANCELED]:
		return False

	# Mark the patient as being messaged as well as the ID of the message,
	#  so we can track if they respond or not and re-send the message as
	#  needed
	oWorkflow['noteId'] = note_id
	oWorkflow['step'] = STEP_ED_PROVIDER_MESSAGED
	oWorkflow['tries'] = 0
	oWorkflow.save()

	# Return OK
	return True

def providerOpens(order_id, user_id, monolith):
	"""Provider Opens

	Called when the provider opens the order record

	Arguments:
		order_id (str): The ID of the order
		user_id (int): The ID of the user (provider)
		monolith (services.monolith.Monolith): An instance of the service used
			to send SMS messages

	Returns:
		bool
	"""

	# Find the order's workflow
	oWorkflow = SMSPatientWorkflow.filter({
		"orderId": order_id,
		"groupId": GROUP_ED
	}, limit=1);

	# If there's no order, assume it's an older customer
	#  and just return
	if not oWorkflow:
		return False

	# If the patient has already been sent the open message
	#  just return
	if oWorkflow['step'] in [STEP_ED_KONNEKTIVE_CANCELED, STEP_ED_PROVIDER_OPENS]:
		return False

	# Find the order
	dOrder = KtOrder.filter(
		{"orderId": order_id},
		raw=['firstName', 'lastName', 'emailAddress', 'phoneNumber', 'state'],
		limit=1
	)
	if not dOrder:
		return False

	# Find the user
	dUser = User.get(user_id, raw=['firstName', 'lastName'])
	if not dUser:
		return False

	# Get the template
	sContent = fetchTemplate(
		oWorkflow['groupId'],
		'async',
		STEP_ED_PROVIDER_OPENS
	);

	# Process the template
	sContent = processTemplate(sContent, dOrder, {
		"provider_name": '%s %s' % (dUser['firstName'], dUser['lastName'])
	});

	# Message data
	dMsg = {
		"_internal_": Services.internalKey(),
		"name": "SMS Workflow",
		"customerPhone": dOrder['phoneNumber'],
		"content": sContent,
		"type": 'support'
	}

	# Send the SMS to the patient
	oResponse = monolith.messageOutgoing_create(dMsg)

	# If there's an error sending the SMS
	if oResponse.errorExists():
		emailError(
			'SMSWorkflow providerOpens Error',
			'Couldn\'t send sms:\n\n%s\n\n%s' % (
				str(dOrder),
				str(oResponse)
			)
		)
		return False

	# Update the workflow step
	oWorkflow['step'] = STEP_ED_PROVIDER_OPENS
	oWorkflow['tries'] = 0
	oWorkflow.save()

	# Return OK
	return True

def shipping(info):
	"""Shipping

	Handles sending out a shipped order SMS

	Arguments:
		info (dict): Tracking info to handle

	Returns:
		None
	"""

	try:

		# Find the workflow
		oWorkflow = SMSPatientWorkflow.filter({
			"customerId": str(info['customerId']),
			"groupId": GROUP_ED
		}, orderby=[['createdAt', 'ASC']], limit=1);

		# Check if the workflow exists
		if not oWorkflow:
			return False

		# Find the order
		dOrder = KtOrder.filter(
			{"customerId": str(info['customerId'])},
			raw=['firstName', 'lastName', 'emailAddress', 'phoneNumber', 'state'],
			orderby=[['dateCreated', 'DESC']],
			limit=1
		);

		# If there's no order or phone number, do nothing
		if not dOrder or not dOrder['phoneNumber'] or \
			dOrder['phoneNumber'].strip() == '':
			return False

		# Find the template
		sContent = fetchTemplate(
			oWorkflow['groupId'], 'async', PACKAGE_SHIPPED
		)

		# Generate the link
		sLink = Shipping.generateLink(info['type'], info['code'])

		# Process the template
		sContent = processTemplate(sContent, dOrder, {
			"tracking_code": info['code'],
			"tracking_link": sLink,
			"tracking_date": info['date']
		});

		# Send the SMS to the patient
		oResponse = Services.create('monolith', 'message/outgoing', {
			"_internal_": Services.internalKey(),
			"store_on_error": True,
			"name": "SMS Workflow",
			"customerPhone": dOrder['phoneNumber'],
			"content": sContent,
			"type": 'support'
		})
		if oResponse.errorExists():
			if oResponse.error['code'] != 1500:
				emailError(
					'SMSWorkflow Shipping Error',
					'Couldn\'t send sms:\n\n%s\n\n%s\n\n%s' % (
						str(info),
						str(dOrder),
						str(oResponse)
					)
				)
			return False

		# Mark the package as shipped if it hasn't already so that we know
		#  the first order was sent
		if oWorkflow['shipped'] == 0:
			oWorkflow['shipped'] = 1
			oWorkflow.save()

	except Exception as e:
		sBody = '%s\n\n%s' % (
			', '.join([str(s) for s in e.args]),
			traceback.format_exc()
		)
		emailError('SMSWorkflow Unknown Error', sBody)
		return False

	# Return OK
	return True
