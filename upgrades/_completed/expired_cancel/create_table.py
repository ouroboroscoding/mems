# coding=utf8
""" Create the expired table"""

# Services
from records.prescriptions import Expiring

def run():

	# Create the tables
	Expiring.tableCreate()

	# Return OK
	return True
