# coding=utf8
"""HRT Workflow

Handles finding the correct customer, generating the template, and sending
off the SMS
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-08-02"

# Python imports
import traceback

# Pip imports
from RestOC import Services

# Record imports
from records.monolith import HrtPatient, KtOrder

# Shared imports
from shared import Shipping

# Local imports
from . import fetchTemplate, processTemplate, GROUP_HRT, GROUP_ZRT_LAB

# HRT Step values
STEP_HRT_KIT_ORDERED			= 21
STEP_HRT_KIT_RETURNED			= 22
STEP_HRT_WATCH_VIDEO			= 23
STEP_HRT_CONDITIONS_NOT_MET		= 24
STEP_HRT_APPROVED				= 25
STEP_HRT_DECLINED				= 26
STEP_HRT_KIT_SHIPPED			= 27
STEP_HRT_KIT_DELIVERED			= 28

# Non step value
PACKAGE_SHIPPED				= 50

def shipping(info):
	"""Shipping

	Handles sending out a shipped order SMS

	Arguments:
		info (dict): Tracking info to handle

	Returns:
		None
	"""

	# Find the patient
	oPatient = HrtPatient.filter({
		"ktCustomerId": str(info['customerId'])
	}, orderby=[['createdAt', 'ASC']], limit=1);

	# Check if the patient exists
	if not oPatient:
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
		GROUP_ZRT_LAB, 'sms', PACKAGE_SHIPPED
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
		"name": "HRT Workflow",
		"customerPhone": dOrder['phoneNumber'],
		"content": sContent,
		"type": 'support'
	})
	if oResponse.errorExists():
		if oResponse.error['code'] != 1500:
			raise Exception(
				'HRT Workflow Shipping Error',
				'Couldn\'t send sms:\n\n%s\n\n%s\n\n%s' % (
					str(info),
					str(dOrder),
					str(oResponse)
				)
			)
		return False

	# Return OK
	return True
