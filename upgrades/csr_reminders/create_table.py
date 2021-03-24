# coding=utf8
""" Create the Reminder table"""

# Services
from records.csr import Reminder

def run():

	# Create the table
	Reminder.tableCreate()

	# Return OK
	return True
