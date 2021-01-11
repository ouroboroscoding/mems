# coding=utf8
""" Create the monolith calendly_event"""

# Services
from records.monolith import CalendlyEvent

def run():

	# Create the tables
	CalendlyEvent.tableCreate()

	# Return OK
	return True
