# coding=utf8
""" Alter the existing tables"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Alter the customer claimed table table
	Record_MySQL.Commands.execute(
		'monolith',
		"ALTER TABLE `monolith`.`customer_claimed` " \
		"ADD COLUMN `continuous` TINYINT(1) NULL AFTER `orderId`;"
	)

	# Alter the order claim table
	Record_MySQL.Commands.execute(
		'monolith',
		"ALTER TABLE `monolith`.`kt_order_claim` " \
		"ADD COLUMN `continuous` TINYINT(1) NOT NULL DEFAULT 0 AFTER `orderId`;"
	)

	# Return OK
	return True
