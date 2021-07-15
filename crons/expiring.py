# coding=utf8
"""Expiring

Handles cancelling purchases related to expiring prescriptions and notifying
customers
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-09-28"

# Pip imports
from RestOC import Conf, Record_MySQL, Services

# Record imports
import arrow
from records.monolith import KtOrderContinuous
from records.prescriptions import Expiring

# Service imports
from services.konnektive import Konnektive

# Cron imports
from crons import isRunning, emailError
from shared import SMSWorkflow

# Globals
_oKNK = None
_dMIP = None

def _stepZero():
	"""Step Zero

	Sends initial SMS with CED MIP link and created continuous order record

	Returns:
		bool
	"""

	# Get all new expirings purchases
	lExpiring = Expiring.filter({
		"step": 0
	})

	# If there's none
	if not lExpiring:
		return True

	# Get the template
	sTemplate = SMSWorkflow.fetchTemplate(0, 'sms', 0)

	# Go through each one
	for o in lExpiring:

		# If it's a Konnekive customer
		if o['crm_type'] == 'knk':

			# Get the purchase info
			lPurchases = _oKNK._request('purchase/query', {
				"purchaseId": o['crm_purchase']
			});

			# If we got nothing, or the status is already cancelled
			if not lPurchases or lPurchases[0]['status'] == 'CANCELLED':

				# Delete it
				o.delete()
				continue

			# Create a new continuous order record
			try:
				oOC = KtOrderContinuous({
					"customerId": int(o['crm_id']),
					"orderId": o['crm_order'],
					"purchaseId": o['crm_purchase'],
					"active": False,
					"status": 'PENDING'
				})
				oOC.create()

				# Process the template
				sContent = SMSWorkflow.processTemplate(sTemplate, lPurchases[0], {
					"mip_link": '%s%s' % (_dMIP['domain'], _dMIP['ced'] % {"customerId": o['crm_id']})
				});

				# Send the SMS to the patient
				oResponse = Services.create('monolith', 'message/outgoing', {
					"_internal_": Services.internalKey(),
					"name": "SMS Workflow",
					"customerPhone": lPurchases[0]['phoneNumber'],
					"content": sContent,
					"type": 'support'
				})
				if oResponse.errorExists():
					emailError('Expiring Error', 'Couldn\'t send sms:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

				# Send the email to the patient
				oResponse = Services.create('communications', 'email', {
					"_internal_": Services.internalKey(),
					"text_body": sContent,
					"subject": 'Your prescription is going to expire',
					"to": lPurchases[0]['emailAddress']
				})
				if oResponse.errorExists():
					emailError('Expiring Error', 'Couldn\'t send email:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

			# Catch duplicate errors on continuous model
			except Record_MySQL.DuplicateException as e:
				pass

			# Update the step
			o['step'] = 1
			o.save()

		else:
			emailError('Expiring Error', 'Unknown CRM: %s' % o['crm_type'])
			continue

	# Return OK
	return True

def _stepOne():
	"""Step One

	Sends follow up SMS if the customer still hasn't completed their CED MIP

	Returns:
		bool
	"""

	# Get all new expirings purchases
	lExpiring = Expiring.filter({
		"step": 1,
		"_updated": {
			"lte": Record_MySQL.Literal('DATE_SUB(now(), INTERVAL 335 HOUR)')
		}
	})

	# If there's none
	if not lExpiring:
		return True

	# Get the template
	sTemplate = SMSWorkflow.fetchTemplate(0, 'sms', 1)

	# Go through each one
	for o in lExpiring:

		# If it's a Konnekive customer
		if o['crm_type'] == 'knk':

			# Look for a continuous order record
			dOC = KtOrderContinuous.filter({
				"customerId": o['crm_id'],
				"orderId": o['crm_order']
			}, raw=['active'], limit=1)

			# If there's none, or it's marked as active
			if not dOC or dOC['active']:

				# Delete the record and move on
				o.delete()
				continue

			# Get the purchase info
			lPurchases = _oKNK._request('purchase/query', {
				"purchaseId": o['crm_purchase']
			});

			# If we got nothing, or the status is already cancelled
			if not lPurchases or lPurchases[0]['status'] == 'CANCELLED':

				# Delete the record and move on
				o.delete()
				continue

			# Process the template
			sContent = SMSWorkflow.processTemplate(sTemplate, lPurchases[0], {
				"mip_link": '%s%s' % (_dMIP['domain'], _dMIP['ced'] % {"customerId": o['crm_id']})
			});

			# Send the SMS to the patient
			oResponse = Services.create('monolith', 'message/outgoing', {
				"_internal_": Services.internalKey(),
				"name": "SMS Workflow",
				"customerPhone": lPurchases[0]['phoneNumber'],
				"content": sContent,
				"type": 'support'
			})
			if oResponse.errorExists():
				emailError('Expiring Error', 'Couldn\'t send sms:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

			# Send the email to the patient
			oResponse = Services.create('communications', 'email', {
				"_internal_": Services.internalKey(),
				"text_body": sContent,
				"subject": 'Your prescription is going to expire',
				"to": lPurchases[0]['emailAddress']
			})
			if oResponse.errorExists():
				emailError('Expiring Error', 'Couldn\'t send email:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

			# Update the step
			o['step'] = 2
			o.save()

		else:
			emailError('Expiring Error', 'Unknown CRM: %s' % o['crm_type'])
			continue

	# Return OK
	return True

def _stepTwo():
	"""Step Two

	Sends follow up SMS if the customer still hasn't completed their CED MIP

	Returns:
		bool
	"""

	# Get all new expirings purchases
	lExpiring = Expiring.filter({
		"step": 2,
		"_updated": {
			"lte": Record_MySQL.Literal('DATE_SUB(now(), INTERVAL 167 HOUR)')
		}
	})

	# If there's none
	if not lExpiring:
		return True

	# Get the template
	sTemplate = SMSWorkflow.fetchTemplate(0, 'sms', 2)

	# Go through each one
	for o in lExpiring:

		# If it's a Konnekive customer
		if o['crm_type'] == 'knk':

			# Look for a continuous order record
			dOC = KtOrderContinuous.filter({
				"customerId": o['crm_id'],
				"orderId": o['crm_order']
			}, raw=['active'], limit=1)

			# If there's none, or it's marked as active
			if not dOC or dOC['active']:

				# Delete the record and move on
				o.delete()
				continue

			# Get the purchase info
			lPurchases = _oKNK._request('purchase/query', {
				"purchaseId": o['crm_purchase']
			});

			# If we got nothing, or the status is already cancelled
			if not lPurchases or lPurchases[0]['status'] == 'CANCELLED':

				# Delete the record and move on
				o.delete()
				continue

			# Process the template
			sContent = SMSWorkflow.processTemplate(sTemplate, lPurchases[0], {
				"mip_link": '%s%s' % (_dMIP['domain'], _dMIP['ced'] % {"customerId": o['crm_id']})
			});

			# Send the SMS to the patient
			oResponse = Services.create('monolith', 'message/outgoing', {
				"_internal_": Services.internalKey(),
				"name": "SMS Workflow",
				"customerPhone": lPurchases[0]['phoneNumber'],
				"content": sContent,
				"type": 'support'
			})
			if oResponse.errorExists():
				emailError('Expiring Error', 'Couldn\'t send sms:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

			# Send the email to the patient
			oResponse = Services.create('communications', 'email', {
				"_internal_": Services.internalKey(),
				"text_body": sContent,
				"subject": 'Your prescription is going to expire',
				"to": lPurchases[0]['emailAddress']
			})
			if oResponse.errorExists():
				emailError('Expiring Error', 'Couldn\'t send email:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

			# Update the step
			o['step'] = 3
			o.save()

		else:
			emailError('Expiring Error', 'Unknown CRM: %s' % o['crm_type'])
			continue

	# Return OK
	return True

def _stepThree():
	"""Step Three

	Pause the purchase and notify the customer

	Returns:
		bool
	"""

	# Get all new expirings purchases
	lExpiring = Expiring.filter({
		"step": 3,
		"_updated": {
			"lte": Record_MySQL.Literal('DATE_SUB(now(), INTERVAL 191 HOUR)')
		}
	})

	# If there's none
	if not lExpiring:
		return True

	# Get a date far in the future
	sPauseDate = arrow.get().shift(years=10).format('MM/DD/YY')

	# Get the template
	sTemplate = SMSWorkflow.fetchTemplate(0, 'sms', 3)

	# Go through each one
	for o in lExpiring:

		# If it's a Konnekive customer
		if o['crm_type'] == 'knk':

			# Look for a continuous order record
			dOC = KtOrderContinuous.filter({
				"customerId": o['crm_id'],
				"orderId": o['crm_order']
			}, raw=['active'], limit=1)

			# If there's none, or it's marked as active
			if not dOC or dOC['active']:

				# Delete the record and move on
				o.delete()
				continue

			# Get the purchase info
			lPurchases = _oKNK._request('purchase/query', {
				"purchaseId": o['crm_purchase']
			});

			# If we got nothing, or the status is already cancelled
			if not lPurchases or lPurchases[0]['status'] == 'CANCELLED':

				# Delete the record and move on
				o.delete()
				continue

			# Pause the purchase so the customer doesn't get billed
			dRes = _oKNK._post('purchase/pause', {
				"purchaseId": o['crm_purchase'],
				"restartDate": sPauseDate
			})

			# If it failed
			if dRes['result'] != 'SUCCESS':
				emailError('Expiring Error', 'Couldn\'t pause purchase:\n\n%s\n\n%s' % (str(o.record()), str(dRes)))
				continue

			# Process the template
			sContent = SMSWorkflow.processTemplate(sTemplate, lPurchases[0], {
				"mip_link": '%s%s' % (_dMIP['domain'], _dMIP['ced'] % {"customerId": o['crm_id']})
			});

			# Send the SMS to the patient
			oResponse = Services.create('monolith', 'message/outgoing', {
				"_internal_": Services.internalKey(),
				"name": "SMS Workflow",
				"customerPhone": lPurchases[0]['phoneNumber'],
				"content": sContent,
				"type": 'support'
			})
			if oResponse.errorExists():
				emailError('Expiring Error', 'Couldn\'t send sms:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

			# Send the email to the patient
			oResponse = Services.create('communications', 'email', {
				"_internal_": Services.internalKey(),
				"text_body": sContent,
				"subject": 'We paused your subscription',
				"to": lPurchases[0]['emailAddress']
			})
			if oResponse.errorExists():
				emailError('Expiring Error', 'Couldn\'t send email:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

			# Update the step
			o['step'] = 4
			o.save()

		else:
			emailError('Expiring Error', 'Unknown CRM: %s' % o['crm_type'])
			continue

	# Return OK
	return True

def _stepFour():
	"""Step Four

	Cancel the purchase and notify the customer

	Returns:
		bool
	"""

	# Get all new expirings purchases
	lExpiring = Expiring.filter({
		"step": 4,
		"_updated": {
			"lte": Record_MySQL.Literal('DATE_SUB(now(), INTERVAL 719 HOUR)')
		}
	})

	# If there's none
	if not lExpiring:
		return True

	# Get the template
	sTemplate = SMSWorkflow.fetchTemplate(0, 'sms', 4)

	# Go through each one
	for o in lExpiring:

		# If it's a Konnekive customer
		if o['crm_type'] == 'knk':

			# Look for a continuous order record
			oOC = KtOrderContinuous.filter({
				"customerId": o['crm_id'],
				"orderId": o['crm_order']
			}, limit=1)

			# If there's none, or it's marked as active
			if not oOC or oOC['active']:

				# Delete the record and move on
				o.delete()
				continue

			# Get the purchase info
			lPurchases = _oKNK._request('purchase/query', {
				"purchaseId": o['crm_purchase']
			});

			# If we got nothing, or the status is already cancelled
			if not lPurchases or lPurchases[0]['status'] == 'CANCELLED':

				# Delete the record and move on
				o.delete()
				continue

			# Pause the purchase so the customer doesn't get billed
			dRes = _oKNK._post('purchase/cancel', {
				"purchaseId": o['crm_purchase'],
				"cancelReason": 'Patient did not fill in C-ED'
			})

			# If it failed
			if dRes['result'] != 'SUCCESS':
				emailError('Expiring Error', 'Couldn\'t cancel purchase:\n\n%s\n\n%s' % (str(o.record()), str(dRes)))
				continue

			# Delete the continuous order
			oOC.delete()

			# Process the template
			sContent = SMSWorkflow.processTemplate(sTemplate, lPurchases[0]);

			# Send the SMS to the patient
			oResponse = Services.create('monolith', 'message/outgoing', {
				"_internal_": Services.internalKey(),
				"name": "SMS Workflow",
				"customerPhone": lPurchases[0]['phoneNumber'],
				"content": sContent,
				"type": 'support'
			})
			if oResponse.errorExists():
				emailError('Expiring Error', 'Couldn\'t send sms:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

			# Send the email to the patient
			oResponse = Services.create('communications', 'email', {
				"_internal_": Services.internalKey(),
				"text_body": sContent,
				"subject": 'We cancelled your subscription',
				"to": lPurchases[0]['emailAddress']
			})
			if oResponse.errorExists():
				emailError('Expiring Error', 'Couldn\'t send email:\n\n%s\n\n%s' % (str(o.record()), str(oResponse)))

			# Update the step
			o['step'] = 5
			o.save()

		else:
			emailError('Expiring Error', 'Unknown CRM: %s' % o['crm_type'])
			continue

	# Return OK
	return True

def run():
	"""Run

	Fetches expiring and notifies customer

	Returns:
		bool
	"""

	global _oKNK, _dMIP

	# If we're already running
	if isRunning('expiring'):
		return True

	# Construct and init Konnektive service
	_oKNK = Konnektive()
	_oKNK.initialise()

	# Get the MIP conf
	_dMIP = Conf.get('mip')

	# Process all the 0 steps (notify of expiration)
	_stepZero()

	# Process all the 1 steps (14 days later, notify again of expiration)
	_stepOne()

	# Process all the 2 steps (7 days later, notify again of expiration)
	_stepTwo()

	# Process all the 3 steps (8 days later, notify of pause on the billing)
	_stepThree()

	# Process all the 4 steps (30 days later, cancel the purchase)
	_stepFour()

	# Return OK
	return True
