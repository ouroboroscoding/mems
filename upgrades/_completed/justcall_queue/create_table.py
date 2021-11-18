# coding=utf8
""" Create necessary tables"""

# Service imports
from records.justcall import QueueCall, QueueNumber

def run():

	# Create the tables
	QueueCall.tableCreate()
	QueueNumber.tableCreate()

	# Return OK
	return True
