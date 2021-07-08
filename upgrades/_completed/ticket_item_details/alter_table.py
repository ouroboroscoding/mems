# coding=utf8
""" Alter the ticket item table"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Add the direction and memo IDs to the table
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`csr_ticket_item` " \
		"ADD COLUMN `direction` ENUM('incoming', 'outgoing') NULL AFTER `type`, " \
		"ADD COLUMN `memo_id` INT NOT NULL DEFAULT 0 AFTER `identifier`, " \
		"ADD INDEX `i_direction_memo` (`direction`, `memo_id`) VISIBLE"
	)

	# Return OK
	return True
