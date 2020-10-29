# coding=utf8
""" Create the new tables"""

# Record imports
from records.patient import AccountSetupAttempt

def run():

	# Create the table
	AccountSetupAttempt.tableCreate()

	# Return OK
	return True
