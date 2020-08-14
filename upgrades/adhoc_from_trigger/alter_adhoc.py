# coding=utf8
""" Alter the adhoc table"""

# Pip imports
from RestOC import Record_MySQL

# Service imports
from records.welldyne import AdHoc, Trigger

def run():

	# Fetch all the current AdHoc
	lAdHoc = Record_MySQL.Commands.select(
		'primary',
		'SELECT * FROM `mems`.`welldyne_adhoc`'
	)

	print(lAdHoc)

	# Drop the sent as it won't be needed anymore
	Record_MySQL.Commands.execute(
		'primary',
		'DROP TABLE IF EXISTS `mems`.`welldyne_adhoc_sent`'
	)

	# Delete all records
	Record_MySQL.Commands.execute(
		'primary',
		'DELETE FROM `mems`.`welldyne_adhoc`'
	)

	# Modify the table
	Record_MySQL.Commands.execute(
		'primary',
		'ALTER TABLE `mems`.`welldyne_adhoc`\n' \
		'DROP COLUMN `crm_order`,\n' \
		'DROP COLUMN `crm_id`,\n' \
		'DROP COLUMN `crm_type`,\n' \
		'ADD COLUMN `trigger_id` CHAR(36) NOT NULL AFTER `_created`,\n' \
		'ADD UNIQUE INDEX `trigger_id` (`trigger_id`),\n' \
		'DROP INDEX `ui_cot`\n'
	)

	# Go through each adhoc
	for d in lAdHoc:

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
			"memo_user": d['memo_user']
		})
		oAdHoc.create()

	# Return OK
	return True
