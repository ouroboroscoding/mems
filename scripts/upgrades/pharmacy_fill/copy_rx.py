# coding=utf8
""" Copy the pharmacy fill errors"""

# Pip imports
import arrow

# Service imports
from services.welldyne.records import OldRxNumber, RxNumber

def run():

	# Fetch all triggers in the old table
	lOld = OldRxNumber.get(raw=True)
	iOld = len(lOld)
	iCount = 1

	# Go through each one and insert it into the new table
	for d in lOld:

		# Inform
		print('\r%d / %d' % (iCount, iOld), end='')
		iCount += 1

		# Create the new instance
		oRxNumber = RxNumber({
			"_created": arrow.get(d['createdAt']).timestamp,
			"_updated": arrow.get(d['updatedAt']).timestamp,
			"member_id": str(d['customerId']).zfill(6),
			"number": d['rx']
		})

		# Create the record
		oRxNumber.create(conflict='replace')

	# Clean console
	print('\nDone')

	# Return OK
	return True
