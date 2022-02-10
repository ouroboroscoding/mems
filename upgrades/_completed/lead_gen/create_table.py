# coding=utf8
""" Create the csr lead table"""

# Records
from records.csr import Lead

def run():

	# Create the tables
	Lead.tableCreate()

	# Return OK
	return True
