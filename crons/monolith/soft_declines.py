# coding=utf8
"""Hard Declines

Fetches soft declines and sends an SMS message to the associated account so the
user is aware of the issue.
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-04-08"

# Python imports
from time import time

# Pip imports
import arrow
from RestOC import Services

# Service imports
from services.konnektive import Konnektive

# Record imports
from records.reports import LastRun

# Cron imports
from crons import emailError, isRunning

# Defines
CRON_NAME = 'monolith_soft_declines'

def run():
	"""Run

	Fetches all the hard declines since the last run and notifies agents of
	the failure

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning(CRON_NAME):
		return True

	# Create a new Konnektive service then initialise it
	oKNK = Konnektive()
	oKNK.initialise()

	# Get the last time the script was run
	oLastRun = LastRun.get(CRON_NAME)
	iLastRun = oLastRun and oLastRun['ts'] or (int(time()) - 21600)

	# Generate the new timestamp
	iTS = int(time())

	# Create the start date/time
	oStart = arrow.get(iLastRun).to('US/Eastern')
	oEnd = arrow.get(iTS).to('US/Eastern')

	# Get the hard declines between the last and current timestamp
	lResults = oKNK._request('transactions/query', {
		"responseType": 'SOFT_DECLINE',
		"startDate": oStart.format('MM/DD/YYYY'),
		"startTime": oStart.format('HH:mm'),
		"endDate": oEnd.format('MM/DD/YYYY'),
		"endTime": oEnd.format('HH:mm')
	})

	# Go through each result
	for d in lResults:

		# If the transaction type is not SALE, AUTHORIZE, or CAPTURE, skip it
		if d['txnType'] not in ['SALE', 'AUTHORIZE', 'CAPTURE']:
			continue

		# If not in ED mids, or recycle is null, skip it
		if d['merchantId'] not in [26,27] or d['recycleNumber'] == None:
			continue

		# If it will be recycled
		if d['recycleNumber'] == 0:

			# If it's not in the first three months
			if d['billingCycleNumber'] not in [1,2,3]:
				continue

			# Generate the message
			sContent = "MALE EXCEL MEDICAL: Mr. %s, we are unable to fulfill " \
						"your prescription due to your payment being declined " \
						"by your bank. We will attempt to process the payment " \
						"and fill your prescription again in the coming days. " \
						"To update your payment method or speak to an agent " \
						"please reply to this message, emailing " \
						"support@maleexcel.com or calling (833)-625-3392. " \
						"Thanks for choosing Male Excel Medical and have a " \
						"great day." % d['lastName']

		# Unknown recycle number
		else:
			emailError('Soft Decline Issue', 'Unknown recycleNumber\n\n%s' % str(d))
			continue

		# Send the message to the customer
		oResponse = Services.create('monolith', 'message/outgoing', {
			"_internal_": Services.internalKey(),
			"auto_response": True,
			"customerPhone": d['phoneNumber'][-10:],
			"content": sContent,
			"name": "SMS Workflow",
			"type": "support"
		})
		if oResponse.errorExists():
			emailError('Soft Decline Failed', 'Failed to send Auto-Response SMS\n\n%s\n\n%s' % (
				str(d),
				str(oResponse)
			))

	# Store the updated timestamp or create a new record
	if oLastRun:
		oLastRun['ts'] = iTS
		oLastRun.save()
	else:
		oLastRun = LastRun({"_id": CRON_NAME, "ts": iTS})
		oLastRun.create()

	# Return OK
	return True
