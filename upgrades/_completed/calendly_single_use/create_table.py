# coding=utf8
""" Create the new table"""

# Record imports
from records.providers import CalendlySingleUse

def run():

	# Create the new table
	CalendlySingleUse.tableCreate()

	# Return OK
	return True
