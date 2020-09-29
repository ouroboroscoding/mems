# coding=utf8
""" Add Templates"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Alter the setup table
	Record_MySQL.Commands.execute(
		'monolith',
		"INSERT INTO `monolith`.`sms_template` (`groupId`, `type`, `step`, `title`, `content`, `createdAt`, `updatedAt`) VALUES ('0', 'sms', '0', 'Expiring Prescription', 'Male Excel Medical: Yo {patient_last}, your prescription is about to expire, please fill out blah blah blah {mip_link}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
	)

	# Return OK
	return True
