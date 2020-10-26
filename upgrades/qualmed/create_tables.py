# coding=utf8
""" Create the Qualified Medication tables"""

# Services
from records.qualmed import Item

def run():

	# Create the tables
	Item.tableCreate()

	# Return OK
	return True
