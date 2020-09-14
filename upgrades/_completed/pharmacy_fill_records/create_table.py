# coding=utf8
""" Create the pharmacy fill table"""

# Records
from records.prescriptions import PharmacyFill

def run():

	# Create the tables
	PharmacyFill.tableCreate()

	# Return OK
	return True
