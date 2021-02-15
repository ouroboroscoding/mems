# coding=utf8
""" Alter the providers_tracking"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Alter the table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`providers_tracking` " \
		"ADD COLUMN `resolution_sesh` CHAR(36) NULL AFTER `resolution`, " \
		"CHANGE COLUMN `action` `action` ENUM('signin', 'viewed') NOT NULL AFTER `memo_id`, " \
		"CHANGE COLUMN `sesh` `action_sesh` CHAR(36) NOT NULL , " \
		"CHANGE COLUMN `start` `action_ts` TIMESTAMP NOT NULL , " \
		"CHANGE COLUMN `end` `resolution_ts` TIMESTAMP NULL DEFAULT NULL"
	)

	# Return OK
	return True
