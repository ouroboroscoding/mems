# coding=utf8
""" Create the Products tables"""

# Services
from records.providers import KnkOrderItem, Provider, Template

def run():

	# Create the tables
	KnkOrderItem.tableCreate()
	Provider.tableCreate()
	Template.tableCreate()

	# Return OK
	return True
