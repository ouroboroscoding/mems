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

	# Return OK
	return True
