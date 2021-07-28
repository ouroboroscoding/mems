# coding=utf8
""" Update the mems `report_last_run` table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Get the existing timestamps
	lRecords = Record_MySQL.Commands.select(
		'primary',
		"SELECT * FROM `mems`.`reports_last_run`"
	)

	# Alter the ts field to allow timestamps or unsigned ints
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`reports_last_run` " \
		"CHANGE COLUMN `ts` `ts` INT(11) UNSIGNED NOT NULL"
	)

	# Go through each record and update it
	for d in lRecords:
		Record_MySQL.Commands.execute(
			'primary',
			"UPDATE `mems`.`reports_last_run` SET " \
			"`ts` = %d " \
			"WHERE `_id` = '%s'" % (
				d['ts'],
				d['_id']
			)
		)

	# Return OK
	return True
