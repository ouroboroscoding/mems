# coding=utf8
""" Alter the claim tables"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Modify the claimed table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `monolith`.`customer_claimed` " \
		"ADD COLUMN `ticket` CHAR(36) NULL AFTER `user`"
	)

	# Modify the claimed table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `monolith`.`kt_order_claim` " \
		"ADD COLUMN `ticket` CHAR(36) NULL AFTER `viewed`",
	)

	# Modify the agent table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`csr_agent` " \
		"DROP COLUMN `claims_timeout`, " \
		"ADD COLUMN `type` VARCHAR(255) NOT NULL DEFAULT 'agent', " \
		"ADD COLUMN `escalate` TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 AFTER `type`"
	)

	# Modify the provider table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`providers_provider` " \
		"DROP COLUMN `claims_timeout`"
	)

	# Return OK
	return True
