# coding=utf8
""" Create the List tables"""

# Services
from records.csr import CustomList, CustomListItem
from records.monolith import CustomerClaimedLast

def run():

	# Create the tables
	CustomerClaimedLast.tableCreate()
	CustomList.tableCreate()
	CustomListItem.tableCreate()

	# Return OK
	return True
