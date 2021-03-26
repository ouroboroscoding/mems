# coding=utf8
""" Create the Requests table"""

# Services
from records.providers import Request

def run():

	# Create the table
	Request.tableCreate()

	# Return OK
	return True
