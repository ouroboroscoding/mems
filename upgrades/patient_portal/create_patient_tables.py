# coding=utf8
""" Create the tables for the patient service """

# Services
from services.patient import Patient

def run():

	# Create the table
	Patient.install()

	# Return OK
	return True
