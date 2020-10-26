# coding=utf8
""" Add Templates"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Alter the setup table
	Record_MySQL.Commands.execute(
		'monolith',
		"INSERT INTO `monolith`.`sms_template` (`groupId`, `type`, `step`, `title`, `content`, `createdAt`, `updatedAt`) "\
		"VALUES ('0', 'sms', '0', 'Expiring Prescription', 'Hey {patient_first},\n\nMale Excel Medical: Your prescription expires this month. Please answer the following questions so we may update your medical file and one of our medical providers will generate a new prescription avoiding any refill interruptions.\n\n1. Was the current prescribed medication working ?\n2. Did you have any side effects?\n3. Have there been any changes in your medical conditions since you first enrolled to our services?\n4. Have there been any changes in your medications since you first enrolled to our services?\n5. Do you get chest pain or become short of breath with any of the following: sexual activity, climbing two flights of stairs, or walking two blocks?\n\nIf you are having issues or would like to speak to an agent directly you can also reach us at (833) 674-0404 and we will assist you with the renewal process.', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
	)

	# Return OK
	return True
