# coding=utf8
"""SMS Workflow

Handles finding the correct customer, generating the template, and sending
off the SMS
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-09-01"

# Python import
import re
import traceback

# Pip imports
import arrow
from RestOC import Conf, JSON, Services

# Shared imports
from shared import Shipping

# Service imports
from records.monolith import KtOrder, SMSPatientWorkflow, SMSTemplate, User

# Cron imports
from crons import emailError

# ED Step values
STEP_KONNEKTIVE_CANCELED	= 0;
STEP_CARD_RECEIVED			= 1;
STEP_ONE_DAY_NOTICE			= 2;
STEP_PROVIDER_OPENS			= 3;
STEP_PROVIDER_DECLINE		= 4;
STEP_PROVIDER_PRE_APPROVES	= 5;
STEP_PROVIDER_APPROVES		= 6;
STEP_PROVIDER_MESSAGED		= 7;
STEP_PATIENT_RESPONDED		= 8;
STEP_ORDER_ARCHIVED			= 9;
STEP_ORDER_CANCELED			= 10;
STEP_MEETING_SET			= 11;
STEP_LEAD					= 12;
STEP_LEAD_NO_ORDER_24		= 13;
STEP_LEAD_NO_ORDER_48		= 14;

# HRT Step values
STEP_KIT_ORDERED			= 21;
STEP_KIT_RETURNED			= 22;
STEP_WATCH_VIDEO			= 23;
STEP_CONDITIONS_NOT_MET		= 24;
STEP_HRT_APPROVED			= 25;
STEP_HRT_DECLINED			= 26;
STEP_KIT_SHIPPED			= 27;
STEP_KIT_DELIVERED			= 28;

# Non step value
PACKAGE_SHIPPED				= 50;
WELCOME						= 51;

# Groups
GROUP_ED		= 1;
GROUP_HAIR_LOSS	= 2;
GROUP_HRT		= 3;
GROUP_ZRT_LAB	= 4;

_dStates = None
"""States"""

_dTemplates = {}
"""Templates"""

_reVar = re.compile(r'{[^}]+?}')
"""Variable regex"""

def fetchState(abbr):
	"""Fetch State

	Returns the full name of the state based on the abbreviation

	Arguments:
		abbr (str): State abbreviation

	Returns:
		str
	"""

	global _dStates

	# If we don't have the stats yet
	if not _dStates:

		# Load the divisions json
		dDivisions = JSON.load('definitions/divisions.json')

		# Store the states
		_dStates = dDivisions.pop('US')

	# Return the name of the state
	return abbr in _dStates and _dStates[abbr] or 'Unknown State'

def fetchTemplate(group, type_, step):
	"""Fetch Template

	Fetches a template from the local cache or from the DB and returns it

	Arguments:
		group (int): The ID of the group the template is in
		type_ (str): The type of template, 'async' vs 'av'
		step (int): The step associated with the template

	Returns:
		str
	"""

	global _dTemplates

	# If we don't have the group
	if group not in _dTemplates:
		_dTemplates[group] = {}

	# If we don't have the type_
	if type_ not in _dTemplates[group]:
		_dTemplates[group][type_] = {}

	# If we don't have the step
	if step not in _dTemplates[group][type_]:

		# Fetch it from the DB
		dTpl = SMSTemplate.filter({
			"groupId": group,
			"type": type_,
			"step": step
		}, raw=['content'], limit=1)

		# Store it
		_dTemplates[group][type_][step] = dTpl['content']

	# Return the template
	return _dTemplates[group][type_][step]

def processTemplate(content, order, misc = {}):
	"""Process Template

	Converts variables within the templates into the data provided

	Arguments:
		content (str): The raw template content
		order (dict): The order associated
		misc (dict): Additional fields that might be set

	Returns:
		str
	"""

	# Look for variables in the content
	lMatches = _reVar.findall(content)

	# If there's any
	if lMatches:

		# Go through each match
		for sMatch in lMatches:

			# Default string replacement
			txt = None

			# Switch through all the possible variables
			if sMatch == '{patient_first}':
				txt = order['firstName'] or ' '

			elif sMatch == '{patient_last}':
				txt = order['lastName'] or ' '

			elif sMatch == '{patient_name}':
				txt = '%s %s' % (
					(order['firstName'] or ' '),
					(order['lastName'] or ' ')
				)

			elif sMatch == '{patient_email}':
				txt = order['emailAddress'] or ' ';

			elif sMatch == '{patient_phone}':
				txt = order['phoneNumber'] or ' ';

			elif sMatch == '{patient_state}':
				txt = fetchState(order['state'])

			elif sMatch == '{provider_name}':
				txt = misc['provider_name'] or  ' '

			elif sMatch == '{brochure_link}':
				txt = misc['brochure_link'] or 'https://maleexcel.com/';

			elif sMatch == '{tracking_code}':
				txt = misc['tracking_code'] or 'TRACKING CODE MISSING';

			elif sMatch == '{tracking_link}':
				txt = misc['tracking_link'] or 'TRACKING LINK MISSING';

			elif sMatch == '{tracking_date}':
				txt = misc['tracking_date'] or 'TRACKING DATE MISSING';

			elif sMatch == '{mip_link}':
				txt = misc['mip_link'] or 'MIP LINK MISSING';

			# If we found something, replace it
			if txt is not None:
				content = content.replace(sMatch, txt)

	# Return the new content
	return content

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
	if oWorkflow['step'] in [STEP_KONNEKTIVE_CANCELED, STEP_PROVIDER_APPROVES]:
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
		oWorkflow['type'],
		STEP_PROVIDER_APPROVES
	);

	# Process the template
	sContent = processTemplate(sContent, dOrder, {
		"provider_name": '% %s' % (dUser['firstName'], dUser['lastName'])
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
	oWorkflow['step'] = STEP_PROVIDER_APPROVES
	oWorkflow['tries'] = 0
	oWorkflow.save()

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
	if oWorkflow['step'] in [STEP_KONNEKTIVE_CANCELED, STEP_PROVIDER_DECLINE]:
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
		oWorkflow['type'],
		STEP_PROVIDER_DECLINE
	);

	# Process the template
	sContent = processTemplate(sContent, dOrder, {
		"provider_name": '% %s' % (dUser['firstName'], dUser['lastName'])
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
	oWorkflow['step'] = STEP_PROVIDER_DECLINE
	oWorkflow['tries'] = 0
	oWorkflow.save();

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
		"orderId": order.order_id,
		"groupId": GROUP_ED
	}, limit=1);

	# If there's no patient, assume it's an older customer and just return
	if not oWorkflow:
		return False

	# If the order is already approved / denied / canceled, ignore this
	if oWorkflow['step'] in [STEP_KONNEKTIVE_CANCELED, STEP_PROVIDER_DECLINE, STEP_PROVIDER_APPROVES, STEP_ORDER_CANCELED]:
		return False

	# Mark the patient as being messaged as well as the ID of the message,
	#  so we can track if they respond or not and re-send the message as
	#  needed
	oWorkflow['noteId'] = note_id
	oWorkflow['step'] = STEP_PROVIDER_MESSAGED
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
	if oWorkflow['step'] in [STEP_KONNEKTIVE_CANCELED, STEP_PROVIDER_OPENS]:
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
		oWorkflow['type'],
		STEP_PROVIDER_OPENS
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
	oWorkflow['step'] = STEP_PROVIDER_OPENS
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
			oWorkflow['groupId'], oWorkflow['type'], PACKAGE_SHIPPED
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
			"name": "SMS Workflow",
			"customerPhone": dOrder['phoneNumber'],
			"content": sContent,
			"type": 'support'
		})
		if oResponse.errorExists():
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
