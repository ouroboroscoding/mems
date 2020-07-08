# coding=utf8
""" Create the User Memo table """

# Services
from services.csr.records import Agent

def run():

	# Create the table
	Agent.tableCreate()

	# Return OK
	return True
