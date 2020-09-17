# coding=utf8
""" Alter the claim table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Alter the setup table
	Record_MySQL.Commands.execute(
		'primary',
		'ALTER TABLE `mems`.`csr_agent` ' \
		'ADD COLUMN `claims_max` TINYINT UNSIGNED NOT NULL DEFAULT 20 AFTER `memo_id`, ' \
		'ADD COLUMN `claims_timeout` TINYINT UNSIGNED NOT NULL DEFAULT 48 AFTER `claims_max`'
	)

	# Return OK
	return True
