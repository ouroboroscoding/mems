# coding=utf8
""" Create the WellDyne tables"""

# Services
from services.prescriptions import Prescriptions
from services.welldyne import WellDyne

def run():

	# Create the tables
	Prescriptions.install()
	WellDyne.install()

	# Return OK
	return True
