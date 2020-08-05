# coding=utf8
""" Copy the triggers"""

# Python imports
import time

# Pip imports
import arrow

# Service imports
from services.konnektive import Konnektive
from services.welldyne.records import OldTrigger, Trigger

def dateToKnk(dt):
	return (
		'%s/%s/%s' % (dt[5:7], dt[8:10], dt[0:4]),
		dt[11:16]
	)

def run():

	# Create a new Konnektive instance
	oKNK = Konnektive()
	oKNK.initialise()

	# Fetch all triggers in the old table
	lOld = OldTrigger.get(raw=True)
	iOld = len(lOld)
	iCount = 1

	# Go through each one and insert it into the new table
	for d in lOld:

		# Inform
		print('\r%d / %d' % (iCount, iOld), end='')
		iCount += 1

		# Init the dict for the record
		dRecord = {
			"_created": arrow.get(d['createdAt']).timestamp,
			"_updated": arrow.get(d['updatedAt']).timestamp,
			"crm_type": 'knk',
			"crm_id": str(d['customerId']),
			"crm_order": '',
			"medication": '',
			"rx_id": '',
			"type": d['type'],
			"opened": d['opened'] or d['shipped'],
			"shipped": d['shipped'],
			"raw": ''
		}

		# Convert data
		lDT = dateToKnk(d['triggered'])

		while True:
			try:
				# Find the latest order before this trigger was created
				lRes = oKNK._request('order/query', {
					"customerId": d['customerId'],
					"sortDir": 0,
					"startDate": "01/01/2010",
					"startTime": "00:00:00",
					"endDate": lDT[0],
					"endTime": lDT[1]
				})

				# If we got a value
				if lRes:
					dRecord['crm_order'] = lRes[0]['orderId']

				# Break out of the loop
				break

			except Exception:
				time.sleep(1)

		# Create the instance
		oTrigger = Trigger(dRecord)
		oTrigger.create(conflict='replace')

	# Clean console
	print('\nDone')

	# Return OK
	return True
