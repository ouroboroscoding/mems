# coding=utf8
""" Create the Customers tables"""

# Services
from records.customers import Address, Customer, Note

def run():

	# Create the tables
	Address.tableCreate()
	Customer.tableCreate()
	Note.tableCreate()

	# Return OK
	return True
