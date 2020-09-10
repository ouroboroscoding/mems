# coding=utf8
""" Alter the patient portal tables"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Alter the setup table
	Record_MySQL.Commands.execute(
		'primary',
		'ALTER TABLE `mems`.`patient_account_setup` ' \
		'CHANGE COLUMN `_id` `_id` CHAR(36) NOT NULL, ' \
		'CHANGE COLUMN `rx_type` `rx_type` ENUM(\'ds\', \'ana\') NULL, ' \
		'CHANGE COLUMN `rx_id` `rx_id` VARCHAR(36) NULL, ' \
		'ADD UNIQUE INDEX `crm` (`crm_type` ASC, `crm_id` ASC)'
	)

	# Alter the account table
	Record_MySQL.Commands.execute(
		'primary',
		'ALTER TABLE `mems`.`patient_account` ' \
		'CHANGE COLUMN `rx_type` `rx_type` ENUM(\'ds\', \'ana\') NULL, ' \
		'CHANGE COLUMN `rx_id` `rx_id` VARCHAR(36) NULL, ' \
		'ADD UNIQUE INDEX `crm` (`crm_type` ASC, `crm_id` ASC)'
	)

	# Return OK
	return True
