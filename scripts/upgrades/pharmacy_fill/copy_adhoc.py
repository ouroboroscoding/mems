# coding=utf8
""" Copy the wd adhoc"""

# Pip imports
import arrow

# Service imports
from services.welldyne.records import OldAdHoc, AdHoc

def run():

	# Fetch all triggers in the old table
	lOld = OldAdHoc.get(raw=True)
	iOld = len(lOld)
	iCount = 1

	# Go through each one and insert it into the new table
	for d in lOld:

		# Inform
		print('\r%d / %d' % (iCount, iOld), end='')
		iCount += 1

		# Create the new instance
		oAdHoc = AdHoc({
			"_created": arrow.get(d['createdAt']).timestamp,
			"crm_type": 'knk',
			"crm_id": str(d['customerId']),
			"crm_order": '',
			"type": d['type'],
			"memo_user": d['user']
		})

		# Create the record
		oAdHoc.create(conflict='replace')

	# Clean console
	print('\nDone')

	# Return OK
	return True
