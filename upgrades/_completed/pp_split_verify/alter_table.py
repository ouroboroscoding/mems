# coding=utf8
""" Alter the verify table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Modify the table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`patient_verify` " \
		"ADD COLUMN `type` ENUM('', 'email', 'forgot') NOT NULL DEFAULT '' AFTER `_account`, " \
		"ADD UNIQUE INDEX `account_type` (`_account` ASC, `type` ASC), " \
		"DROP PRIMARY KEY;"
	)

	# Return OK
	return True
