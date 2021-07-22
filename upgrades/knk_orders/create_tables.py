# coding=utf8
""" Create the konnektive tables"""

# Services
from records.konnektive import Campaign, CampaignProduct

def run():

	# Create the tables
	Campaign.tableCreate()
	CampaignProduct.tableCreate()

	# Return OK
	return True
