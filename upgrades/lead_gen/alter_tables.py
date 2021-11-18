# coding=utf8
""" Alter the ticket tables to add leads"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Add opened type to tickets
	Record_MySQL.Commands.execute(
		'primary',
		'ALTER TABLE `mems`.`csr_ticket_opened`\n' \
		'CHANGE COLUMN `type` `type` ENUM(\'Call\', \'E-mail\', \'Follow Up\', \'Lead\', \'Provider\', \'Script Entry\', \'SMS / Voicemail\') NOT NULL'
	)

	# Add resolved types to tickets
	Record_MySQL.Commands.execute(
		'primary',
		'ALTER TABLE `mems`.`csr_ticket_resolved`\n' \
		'CHANGE COLUMN `type` `type` ENUM(\'Contact Attempted\', \'Follow Up Complete\', \'Information Provided\', \'Issue Resolved\', \'Lead Upsold\', \'Lead Not Interested\', \'Provider Confirmed Prescription\', \'QA Order Declined\', \'Recurring Purchase Canceled\', \'Script Entered\', \'Invalid Transfer: No Purchase Information\') NOT NULL'
	)

	# Return OK
	return True
