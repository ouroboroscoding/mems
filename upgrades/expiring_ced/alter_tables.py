# coding=utf8
""" Alter the existing tables"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Update the claims table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`prescriptions_expiring` " \
		"ADD COLUMN `crm_order` VARCHAR(36) NOT NULL AFTER `crm_id`," \
		"DROP INDEX `ui_crm` ," \
		"ADD UNIQUE INDEX `ui_crm` (`crm_type`, `crm_id`, `crm_order`, `crm_purchase`) VISIBLE;"
	)

	# Return OK
	return True
