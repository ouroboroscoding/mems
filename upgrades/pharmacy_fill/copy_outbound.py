# coding=utf8
""" Copy the wd outbound"""

# Pip imports
import arrow

# Service imports
from services.welldyne.records import OldOutreach, Outbound

def run():

	# Fetch all triggers in the old table
	lOld = OldOutreach.get(raw=True)
	iOld = len(lOld)
	iCount = 1

	# Go through each one and insert it into the new table
	for d in lOld:

		# Inform
		print('\r%d / %d' % (iCount, iOld), end='')
		iCount += 1

		# Create the new instance
		oOutbound = Outbound({
			"_created": arrow.get(d['createdAt']).timestamp,
			"crm_type": 'knk',
			"crm_id": str(d['customerId']),
			"crm_order": '',
			"queue": d['queue'],
			"reason": d['reason'],
			"wd_rx": d['rx'],
			"ready": d['ready']
		})

		# Create the record
		oOutbound.create(conflict='replace')

	# Clean console
	print('\nDone')

	# Return OK
	return True
