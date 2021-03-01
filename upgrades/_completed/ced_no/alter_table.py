# coding=utf8
""" Alter the adhoc table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Modify the table
	Record_MySQL.Commands.execute(
		'primary',
		'ALTER TABLE `monolith`.`kt_order_continuous` ' \
		'ADD COLUMN `medsNotWorking` TINYINT(1) NULL DEFAULT 0 AFTER `active`'
	)

	# Return OK
	return True
