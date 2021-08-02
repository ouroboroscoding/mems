
# Python import
import re

# Pip imports
from RestOC import JSON, Services

# Record imports
from records.monolith import SMSTemplate

# Groups
GROUP_ED		= 1
GROUP_HAIR_LOSS	= 2
GROUP_HRT		= 3
GROUP_ZRT_LAB	= 4

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
