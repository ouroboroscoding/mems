# coding=utf8
""" Copy the triggers"""

# Pip imports
import arrow

# Service imports
from services.welldyne.records import OldTrigger, Trigger

def run():

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

		# Create the instance
		oTrigger = Trigger(dRecord)
		oTrigger.create(conflict='replace')

	# Clean console
	print('\nDone')

	# Return OK
	return True
