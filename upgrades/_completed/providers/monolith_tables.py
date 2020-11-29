# coding=utf8
""" Create the Monolith tables"""

# Record imports
from records.monolith import Campaign, KtOrderClaim

def run():

	# Create the tables
	Campaign.tableCreate()
	KtOrderClaim.tableCreate()

	# Return OK
	return True
