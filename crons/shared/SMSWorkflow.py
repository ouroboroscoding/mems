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
from RestOC import Conf, Services

# Shared imports
from shared import JSON, Shipping

# Service imports
from records.monolith import KtOrder, SMSPatientWorkflow, SMSTemplate

# Cron imports
from crons import emailError

# Step values
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

	# If any values are missing
	if not order:
		pat = {}

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

			# If we found something, replace it
			if txt is not None:
				content = content.replace(sMatch, txt)

	# Return the new content
	return content

def shipping(codes):
	"""Shipping

	Handles sending out a shipped order SMS

	Arguments:
		codes (dict[]): A list of tracking info to go through

	Returns:
		None
	"""

	# Go through each item in the list
	for d in codes:

		try:

			# Find the workflow
			oWorkflow = SMSPatientWorkflow.filter({
				"customerId": str(d['customerId']),
				"groupId": GROUP_ED
			}, orderby=[['createdAt', 'ASC']], limit=1);

			# Check if the workflow exists
			if not oWorkflow:
				continue

			# Find the order
			dOrder = KtOrder.filter(
				{"customerId": d['customerId']},
				raw=['firstName', 'lastName', 'emailAddress', 'phoneNumber', 'state'],
				orderby=[['dateCreated', 'DESC']],
				limit=1
			);

			# If there's no order or phone number, do nothing
			if not dOrder or not dOrder['phoneNumber'] or dOrder['phoneNumber'].strip() == '':
				continue

			# Find the template
			sContent = fetchTemplate(
				oWorkflow['groupId'], oWorkflow['type'], PACKAGE_SHIPPED
			)

			# Generate the link
			sLink = Shipping.generateLink(d['type'], d['code'])

			# Process the template
			sContent = processTemplate(sContent, dOrder, {
				"tracking_code": d['code'],
				"tracking_link": sLink,
				"tracking_date": d['date']
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
				emailError('SMSWorkflow Shipping Error', 'Couldn\'t send sms:\n\n%s' % str(d))
				continue

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
			continue
