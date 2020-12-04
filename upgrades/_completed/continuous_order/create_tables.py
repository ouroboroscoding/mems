# coding=utf8
""" Create the Continuous Order table"""

# Services
from records.monolith import KtOrderContinuous

def run():

	# Create the tables
	KtOrderContinuous.tableCreate()

	# Return OK
	return True
