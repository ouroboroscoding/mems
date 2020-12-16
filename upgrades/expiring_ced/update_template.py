# coding=utf8
""" Update the expiring SMS template"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Update the template
	Record_MySQL.Commands.execute(
		'primary',
		"UPDATE `monolith`.`sms_template` SET `content` = 'Hi {patient_first},\n\nMale Excel Medical: Your prescription expires this month. Please answer the following questions so we may update your medical file and one of our medical providers will generate a new prescription avoiding any refill interruptions.\n\n{mip_link}\n\nIf you are having issues or would like to speak to an agent directly you can also reach us at (833) 674-0404 and we will assist you with the renewal process.' " \
		"WHERE `groupId` = 0 " \
		"AND `type` = 'sms' " \
		"AND `step` = 0"
	)

	# Return OK
	return True
