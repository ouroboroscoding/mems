# coding=utf8
""" Create the Link tables"""

from records.link import ViewRecord, UrlRecord

def run():

	# Create the tables
	ViewRecord.tableCreate()
	UrlRecord.tableCreate()

	# Return OK
	return True
