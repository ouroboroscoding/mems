# coding=utf8
""" Finalize the alter to the ticket item table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Add the direction and memo IDs to the table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`csr_ticket_item` " \
		"CHANGE COLUMN `direction` `direction` ENUM('incoming', 'outgoing') NOT NULL"
	)

	# Return OK
	return True
