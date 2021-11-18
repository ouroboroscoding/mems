# coding=utf8
""" Alter the current tables"""

# Pip imports
from RestOC import Record_MySQL

# Record imports
from records.prescriptions import Product

def run():

	# Drop the old table
	Product.tableDrop()

	# Create the new table
	Product.tableCreate()

	# Add the products
	Record_MySQL.Commands.execute(
		'primary',
		"INSERT INTO `mems`.`prescriptions_product` (`_id`, `title`, `type`, `pharmacy`, `display`, `ndc`, `quantity`, `supply`, `directions`, `unit_id`) VALUES\n" \
		"(UUID(), 'WellDyne Tadalafil 20mg Tablet', 'ed', '56387', 'Tadalafil 20mg Tablet', '69238134903', '6', '30', '1 tablet 3-4 hours before sexual activity as needed.  Maximum dose is 1 pill every 3 days.', '26'),\n" \
		"(UUID(), 'WellDyne Sildenafil 100 mg tablet', 'ed', '56387', 'Sildenafil 100 mg tablet', '00093534301', '6', '30', 'Take one tab by mouth once daily 60 minutes prior to sexual activity as needed.', '26'),\n" \
		"(UUID(), 'WellDyne Sildenafil 50mg/100 mg tablet', 'ed', '56387', 'Sildenafil 100 mg tablet', '00093534301', '6', '30', 'Initial dose patient to cut tab in half to take 50mg by mouth qday 60 mins prior to sexual activity. May increase to 100mg qday as tolerated.', '26'),\n" \
		"(UUID(), 'WellDyne Tadalafil 5mg Tablet', 'ed', '56387', 'Tadalafil 5mg Tablet', '00093301756', '30', '30', '1 tab po qday', '26')"
	)

	# Add the approved field to product_to_rx
	Record_MySQL.Commands.execute(
		'primary',
		"ALTER TABLE `mems`.`providers_product_to_rx` " \
		"ADD COLUMN `approved` TINYINT(1) NOT NULL DEFAULT 0 AFTER `ds_id`"
	)

	# Set all existing approved to true
	Record_MySQL.Commands.execute(
		'primary',
		"UPDATE `mems`.`providers_product_to_rx` SET " \
		"	`approved` = 1"
	)

	# Return OK
	return True
