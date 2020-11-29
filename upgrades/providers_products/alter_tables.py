# coding=utf8
""" Alter the provider item to rx table"""

# Pip imports
from RestOC import Record_MySQL

# Record imports
from records.providers import ProductToRx

def run():

	# Delete the old table
	Record_MySQL.Commands.execute(
		'primary',
		'DROP table `mems`.`providers_item_to_rx`'
	)

	# Create the new table
	ProductToRx.tableCreate()

	# Return OK
	return True
