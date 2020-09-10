# coding=utf8
""" Alter the patient portal tables"""

# Record imports
from records.welldyne import NeverStarted

def run():

	# Create the new table
	NeverStarted.tableCreate()

	# Return OK
	return True
