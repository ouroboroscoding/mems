# coding=utf8
""" Add the order IDs to the expiring tables"""

# Pip imports
from RestOC import Record_MySQL

# Service imports
from services.konnektive import Konnektive

def run():

	print('Adding `crm_order` field')

	# Alter the expiring table to add the order
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`prescriptions_expiring` " \
		"ADD COLUMN `crm_order` VARCHAR(36) NULL AFTER `crm_id`"
	)

	# Create a Konnektive instance and init it
	oKNK = Konnektive()
	oKNK.initialise()

	print('Fetching existing records')

	# Get all the current expiring
	lRecords = Record_MySQL.Commands.select(
		'primary',
		'SELECT `_id`, `crm_purchase` FROM `mems`.`prescriptions_expiring`'
	)

	print('Found %d records' % len(lRecords))

	# Go through each record found
	i = 0
	for d in lRecords:

		# Notify of work
		i += 1
		print('\rWorking on %d' % i, end='')

		# Find the purchase in KNK
		lRes = oKNK._request('purchase/query', {
			"purchaseId": d['crm_purchase']
		})

		# Add the order ID
		Record_MySQL.Commands.execute(
			'primary',
			"UPDATE `mems`.`prescriptions_expiring` SET `crm_order` = '%s' " \
			"WHERE `_id` = '%s'" % (
				len(lRes) and lRes[0]['orderId'] or '',
				d['_id']
			)
		)

	print('\rDone')

	print('Creating new index')

	# Alter the expiring table to make the order NOT NULL, and redo the index
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`prescriptions_expiring` " \
		"CHANGE COLUMN `crm_order` `crm_order` VARCHAR(36) NOT NULL, " \
		"DROP INDEX `ui_crm`, " \
		"ADD UNIQUE INDEX `ui_crm` (`crm_type`, `crm_id`, `crm_order`, `crm_purchase`) VISIBLE"
	)

	# Return OK
	return True
