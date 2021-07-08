# coding=utf8
""" Alter the agent table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Drop the sent as it won't be needed anymore
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`csr_agent` " \
		"ADD COLUMN `oof` TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 AFTER `claims_max`, " \
		"ADD COLUMN `oof_replacement` INT NOT NULL DEFAULT 0 AFTER `oof`"
	)

	# Return OK
	return True
