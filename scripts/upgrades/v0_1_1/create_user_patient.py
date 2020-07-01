# coding=utf8
""" Create the User Patient table """

# Services
from services.auth.records import UserPatient

def run():

	# Create the table
	UserPatient.tableCreate()

	# Return OK
	return True
