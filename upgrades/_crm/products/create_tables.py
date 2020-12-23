# coding=utf8
""" Create the Products tables"""

# Services
from records.products import Group, Medication, Product

def run():

	# Create the tables
	Group.tableCreate()
	Medication.tableCreate()
	Product.tableCreate()

	# Return OK
	return True
