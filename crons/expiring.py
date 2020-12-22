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
from RestOC import Conf, Services
from RestOC.Record_MySQL import DuplicateException

# Record imports
from records.monolith import KtOrderContinuous
from records.prescriptions import Expiring

# Service imports
from services.konnektive import Konnektive

# Cron imports
from crons import isRunning, emailError
from shared import SMSWorkflow

def _stepZero():
	"""Step Zero

	Cancels purchase and sends initial SMS

	Returns:
		bool
	"""

	# Get the MIP conf
	dMIP = Conf.get('mip')

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

				# Find the template
				sContent = SMSWorkflow.fetchTemplate(0, 'sms', 0)

				# Process the template
				sContent = SMSWorkflow.processTemplate(sContent, lPurchases[0], {
					"mip_link": '%s%s' % (dMIP['domain'], dMIP['ced'] % {"customerId": o['crm_id']})
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

			# Catch duplicate errors on continuous model
			except DuplicateException as e:
				pass

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
