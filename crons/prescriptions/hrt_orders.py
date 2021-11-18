# coding=utf8
"""HRT Orders

Fetches latest knk orders in the HRT campaigns and adds them to the table if
they fit the profile for needing prescriptions
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-08-23"

# Python imports
from time import time

# Pip imports
import arrow
from RestOC import Services

# Service imports
from services.konnektive import Konnektive

# Record imports
from records.prescriptions import HrtOrder
from records.reports import LastRun

# Cron imports
from crons import emailError, isRunning

# Defines
CRON_NAME = 'prescriptions_hrt_orders'

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
	iLastRun = oLastRun and (oLastRun['ts'] - 60) or (int(time()) - 1800)

	# Generate the new timestamp
	iTS = int(time())

	# Create the start date/time
	oStart = arrow.get(iLastRun).to('US/Eastern')
	oEnd = arrow.get(iTS).to('US/Eastern')

	# Get the hard declines between the last and current timestamp
	lResults = oKNK._request('order/query', {
		"orderStatus": 'COMPLETE',
		"campaignId": '121, 123, 138',
		"startDate": oStart.format('MM/DD/YYYY'),
		"startTime": oStart.format('HH:mm'),
		"endDate": oEnd.format('MM/DD/YYYY'),
		"endTime": oEnd.format('HH:mm')
	})

	# Go through each result
	for d in lResults:

		# If it's not a real card
		if d['cardType'] == 'TESTCARD':
			continue

		# If the amount isn't valid, skip it
		if d['price'] in [None, '0.00', '30.00']:
			continue

		# Create the record instance
		oHrtOrder = HrtOrder({
			"crm_type": 'knk',
			"crm_id": str(d['customerId']),
			"crm_order": d['orderId'],
			"amount": d['price'],
			"date": d['dateCreated'][0:10]
		})

		# Add it to the DB, ignore duplicates
		oHrtOrder.create(conflict='ignore')

	# Store the updated timestamp or create a new record
	if oLastRun:
		oLastRun['ts'] = iTS
		oLastRun.save()
	else:
		oLastRun = LastRun({"_id": CRON_NAME, "ts": iTS})
		oLastRun.create()

	# Return OK
	return True
