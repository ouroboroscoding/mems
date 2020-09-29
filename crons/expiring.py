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
from RestOC import Services

# Record imports
from records.prescriptions import Expiring

# Service imports
from services.konnektive import Konnektive

# Cron imports
from crons import isRunning, emailError
from crons.shared import SMSWorkflow

def _stepZero():
	"""Step Zero

	Cancels purchase and sends initial SMS

	Returns:
		bool
	"""

	# Initialise service instances
	oKNK = Konnektive()
	oKNK.initialise()

	# Get all new expirings purchases
	lExpiring = Expiring.filter({
		"step": 0
	})

	# Go through each one
	for o in lExpiring:

		# If it's a Konnekive customer
		if o['crm_type'] == 'knk':

			# Get the purchase info
			lPurchases = oKNK._request('purchase/query', {
				"purchaseId": o['crm_purchase']
			});

			# If we got nothing
			if not lPurchases:

				# Delete it
				o.delete()
				continue

			# Cancel the purchase
			bRes = oKNK._post('purchase/cancel', {
				"purchaseId": o['crm_purchase']
			})
			bRes = True

			# If it's cancelled
			if bRes:

				# Find the template
				sContent = SMSWorkflow.fetchTemplate(0, 'sms', 0)

				# Generate the MIP link
				sLink = 'https://some_link.com/'

				# Process the template
				sContent = SMSWorkflow.processTemplate(sContent, lPurchases[0], {
					"mip_link": sLink
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
					emailError('Expiring Error', 'Couldn\'t send sms:\n\n%s' % str(o.record()))
					return

				# Update the step
				o['step'] = 1
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

	# If we're already running
	if isRunning('expiring'):
		return True

	# Process all the 0 steps
	return _stepZero()
