# coding=utf8
""" Create the Products tables"""

# Services
from records.providers import ItemToRX, Provider, RoundRobinAgent, Template

def run():

	# Create the tables
	ItemToRX.tableCreate()
	Provider.tableCreate()
	RoundRobinAgent.tableCreate()
	Template.tableCreate()

	# Return OK
	return True
