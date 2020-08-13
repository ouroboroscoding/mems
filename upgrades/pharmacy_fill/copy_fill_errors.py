# coding=utf8
""" Copy the pharmacy fill errors"""

# Pip imports
import arrow

# Service imports
from services.monolith.records import PharmacyFillError as Old
from services.prescriptions.records import PharmacyFillError

def run():

	# Fetch all triggers in the old table
	lOld = Old.get(raw=True)
	iOld = len(lOld)
	iCount = 1

	# Go through each one and insert it into the new table
	for d in lOld:

		# Inform
		print('\r%d / %d' % (iCount, iOld), end='')
		iCount += 1

		# Create the new instance
		oError = PharmacyFillError({
			"_created": arrow.get(d['createdAt']).timestamp,
			"_updated": arrow.get(d['updatedAt']).timestamp,
			"crm_type": 'knk',
			"crm_id": str(d['customerId']),
			"crm_order": d['orderId'],
			"list": d['list'] == 'outreach' and 'outbound' or d['list'],
			"type": d['type'],
			"reason": d['reason'],
			"fail_count": d['failCount'],
			"ready": d['ready']
		})

		# Create the record
		oError.create(conflict='replace')

	# Clean console
	print('\nDone')

	# Return OK
	return True
