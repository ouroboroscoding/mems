# coding=utf8
""" Create the csr agent office hours table"""

# Services
from records.csr import AgentOfficeHours

def run():

	# Create the tables
	AgentOfficeHours.tableCreate()

	# Return OK
	return True
