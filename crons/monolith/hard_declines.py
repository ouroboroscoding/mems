# coding=utf8
"""Hard Declines

Fetches hard declines and adds a fake SMS message to the associated account
so agents are aware of the issue.
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-03-22"

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
CRON_NAME = 'monolith_hard_declines'

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
		"responseType": 'HARD_DECLINE',
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

		# If it's a duplicate transaction, no need to notify the customer
		if 'Duplicate transaction' in d['responseText']:
			continue

		# Add the decline as an incoming SMS
		oResponse = Services.create('monolith', 'message/incoming', {
			"_internal_": Services.internalKey(),
			"customerPhone": d['phoneNumber'][-10:],
			"recvPhone": "0000000000",
			"content": "HARD DECLINE:\n%s" % d['responseText']
		})
		if oResponse.errorExists():
			emailError('Hard Declines Failed', 'Failed to add SMS\n\n%s\n\n%s' % (
				str(d),
				str(oResponse)
			))

		# Generate the message
		sContent = "MALE EXCEL MEDICAL: Mr. %s, we have attempted to bill " \
					"your card however we were unsuccessful. We will reach " \
					"out to assist you with this billing issue or you can " \
					"contact us by replying to this message, emailing " \
					"support@maleexcel.com or calling (833)-625-3392. " \
					"Please note that you will no longer receive your " \
					"prescribed medication until this billing issue has " \
					"been resolved. Thank you again for choosing Male Excel " \
					"Medical and have a great day." % d['lastName']

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
			emailError('Hard Decline Failed', 'Failed to send Auto-Response SMS\n\n%s\n\n%s' % (
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
