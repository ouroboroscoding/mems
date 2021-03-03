# coding=utf8
""" Alter the stats table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Add the 'sms' type to the actions
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`providers_tracking` " \
		"CHANGE COLUMN `action` `action` ENUM('signin', 'viewed', 'sms') NOT NULL"
	)

	# Rename 'x' to 'closed'
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`providers_tracking` " \
		"CHANGE COLUMN `resolution` `resolution` ENUM('signout', 'new_signin', 'approved', 'declined', 'transferred', 'closed') NULL DEFAULT NULL"
	)

	# Update blank records to 'closed'
	Record_MySQL.Commands.execute(
		'primary',
		"UPDATE `mems`.`providers_tracking` SET " \
		"`resolution` = 'closed' " \
		"WHERE `resolution` = ''"
	)

	# Add the 'timeout' type to the resolutions
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`providers_tracking` " \
		"CHANGE COLUMN `resolution` `resolution` ENUM('signout', 'new_signin', 'timeout', 'approved', 'declined', 'transferred', 'closed') NULL DEFAULT NULL"
	)

	# Return OK
	return True
