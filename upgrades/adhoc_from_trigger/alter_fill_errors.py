# coding=utf8
""" Alter the pharmacy_fill_error table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Modify the table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`prescriptions_pharmacy_fill_error`\n" \
		"DROP COLUMN `type`,\n" \
		"CHANGE COLUMN `list` `list` ENUM('fill', 'outreach') NOT NULL"
	)

	# Return OK
	return True
