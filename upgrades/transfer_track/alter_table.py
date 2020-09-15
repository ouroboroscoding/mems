# coding=utf8
""" Alter the claim table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Alter the setup table
	Record_MySQL.Commands.execute(
		'monolith',
		'ALTER TABLE `monolith`.`customer_claimed` ' \
		'ADD COLUMN `transferredBy` VARCHAR(45) NULL AFTER `user`'
	)

	# Return OK
	return True
