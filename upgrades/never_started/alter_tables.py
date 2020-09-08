# coding=utf8
""" Alter the trigger table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Alter the setup table
	Record_MySQL.Commands.execute(
		'primary',
		'ALTER TABLE `mems`.`welldyne_trigger` ' \
		'ADD COLUMN `opened_stage` VARCHAR(127) NULL DEFAULT NULL AFTER `opened`, ' \
		'ADD COLUMN `cancelled` DATETIME NULL DEFAULT NULL AFTER `shipped`'
	)

	# Return OK
	return True
