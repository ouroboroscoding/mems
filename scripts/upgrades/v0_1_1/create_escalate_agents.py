# coding=utf8
""" Install Services

Adds global tables
"""

# Services
from services.csr.records import EscalateAgent

def run():

	# Create the table
	EscalateAgent.tableCreate()

	# Return OK
	return True
