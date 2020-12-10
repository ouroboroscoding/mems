# coding=utf8
""" Create the Provders Tracking tables"""

# Services
from records.providers import Tracking

def run():

	# Create the tables
	Tracking.tableCreate()

	# Return OK
	return True
