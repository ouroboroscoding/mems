# coding=utf8
""" Create the Customers tables"""

# Services
from records.reports import LastRun

def run():

	# Create the table
	LastRun.tableCreate()

	# Return OK
	return True
