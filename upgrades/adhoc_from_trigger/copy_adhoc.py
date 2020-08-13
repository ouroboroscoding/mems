# coding=utf8
""" Copy AdHocs in Fill Errors back into AdHoc"""

# Pip imports
from RestOC import Record_MySQL

# Service imports
from records.welldyne import AdHoc, Trigger

def run():

	# Get all the 'adhoc' records from pharmacy_fill_errors
	lAdHocErrors = Record_MySQL.Commands.select(
		'primary',
		"SELECT * FROM `mems`.`prescriptions_pharmacy_fill_error`\n" \
		"WHERE `list` = 'adhoc'"
	)

	print(lAdHocErrors)

	# Go through each error
	for d in lAdHocErrors:

		# If there's no order, skip it
		if not d['crm_order']:
			continue

		# Try to find an associated trigger
		dTrigger = Trigger.filter({
			"crm_type": d['crm_type'],
			"crm_id": d['crm_id'],
			"crm_order": d['crm_order']
		}, raw=['_id', 'raw'], limit=1)

		# If we didn't find a trigger
		if not dTrigger:
			print('Failed to find a trigger for %s' % d['_id'])
			continue

		# If we found a trigger but there's no raw data
		if not dTrigger['raw']:
			print('Trigger %s has no raw data for %s' % (dTrigger['_id'], d['_id']))
			continue

		# Create the new adhoc
		oAdHoc = AdHoc({
			"_created": d['_created'],
			"trigger_id": dTrigger['_id'],
			"type": d['type'],
			"memo_user": 0
		})
		oAdHoc.create()

	# Delete all the 'adhoc' records from pharmacy_fill_errors
	lAdHocErrors = Record_MySQL.Commands.execute(
		'primary',
		"DELETE FROM `mems`.`prescriptions_pharmacy_fill_error`\n" \
		"WHERE `list` = 'adhoc'"
	)

	# Return OK
	return True
