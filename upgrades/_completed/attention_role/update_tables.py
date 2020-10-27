# coding=utf8
""" Update the existing tables"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Update the claims table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `monolith`.`customer_claimed` " \
		"ADD COLUMN `orderId` CHAR(10) NULL AFTER `user`, " \
		"ADD COLUMN `provider` INT NULL AFTER `orderId`;"
	)

	# Return OK
	return True
