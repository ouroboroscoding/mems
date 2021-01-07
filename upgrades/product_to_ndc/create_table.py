# coding=utf8
""" Create the Prescriptions product"""

# Services
from records.prescriptions import Product

def run():

	# Create the tables
	Product.tableCreate()

	# Return OK
	return True
