# coding=utf8
""" Create the Products tables"""

# Services
from records.providers import Provider, Template
from records.qualmed import KnkOrder

def run():

	# Create the tables
	KnkOrder.tableCreate()
	Provider.tableCreate()
	Template.tableCreate()

	# Return OK
	return True
