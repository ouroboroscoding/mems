# coding=utf8
""" Alter the current permissions"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Update all the csr_overwrite rights to add the read permission
	Record_MySQL.Commands.execute(
		'primary',
		"UPDATE `mems`.`auth_permission` SET " \
		"	`rights` =  `rights` | 1 " \
		"WHERE `name` = 'csr_overwrite'"
	)

	# Return OK
	return True
