# coding=utf8
""" Alter the existing tables"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Update the claims table
	Record_MySQL.Commands.execute(
		'monolith',
		"ALTER TABLE `monolith`.`sms_stop` " \
		"ADD COLUMN `agent` INT NULL AFTER `service`;"
	)

	# Return OK
	return True
