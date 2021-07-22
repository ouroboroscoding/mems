# coding=utf8
""" Add the last_run record for customer_reviews"""

# Record imports
from records.reports import LastRun

def run():

	# Add the record
	oLastRun = LastRun({
		'_id': 'monolith_customer_reviews',
		'ts': 0
	})
	oLastRun.create()

	# Return OK
	return True
