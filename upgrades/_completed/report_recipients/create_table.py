# coding=utf8
""" Create the Recipient table"""

# Services
from records.reports import Recipients

def run():

	# Create the table
	Recipients.tableCreate()

	# Return OK
	return True
