# coding=utf8
""" Create the justcall agent to memo id table"""

# Services
from records.justcall import MemoId

def run():

	# Create the tables
	MemoId.tableCreate()

	# Return OK
	return True
