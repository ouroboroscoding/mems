# coding=utf8
""" Create the Escalate Agent table """

# Services
from services.csr.records import EscalateAgent

def run():

	# Create the table
	EscalateAgent.tableCreate()

	# Return OK
	return True
