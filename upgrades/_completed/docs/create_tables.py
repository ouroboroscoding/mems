# coding=utf8
""" Create the Docs tables"""

# Services
from records.docs import ServiceRecord, NounRecord, ErrorRecord

def run():

	# Create the tables
	ServiceRecord.tableCreate()
	NounRecord.tableCreate()
	ErrorRecord.tableCreate()

	# Return OK
	return True
