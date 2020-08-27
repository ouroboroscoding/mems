# coding=utf8
""" Create the WellDyne tables"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Rename the permissions
	Record_MySQL.Commands.execute(
		'primary',
		"UPDATE `mems`.`auth_permission` SET `name` = 'welldyne_outbound' WHERE `name` = 'welldyne_outreach'"
	)

	# Return OK
	return True
