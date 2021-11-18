# coding=utf8
""" Create necessary tables"""

# Service imports
from records.csr import Action

def run():

	# Create the table
	Action.tableCreate()

	# Return OK
	return True
