# coding=utf8
""" Alter the existing tables"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Alter the customer claimed table
	Record_MySQL.Commands.execute(
		'monolith',
		"ALTER TABLE `monolith`.`customer_claimed` " \
		"ADD COLUMN `viewed` TINYINT(1) NOT NULL DEFAULT 1 AFTER `transferredBy`"
	)

	# Alter the order claimed table
	Record_MySQL.Commands.execute(
		'monolith',
		"ALTER TABLE `monolith`.`kt_order_claim` " \
		"ADD COLUMN `viewed` TINYINT(1) NOT NULL DEFAULT 1 AFTER `transferredBy`"
	)

	# Return OK
	return True
