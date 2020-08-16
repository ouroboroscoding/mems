# coding=utf8
"""Claims Timeout

Removes all claims older than X time
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-14"

# Python imports
import csv
import io
import traceback

# Pip imports
import arrow
from RestOC import Conf, DictHelper

# Record imports
from records.monolith import CustomerClaimed

# Cron imports
from crons import emailError, isRunning

def run(period=None):
	"""Run

	Fetches all the adhoc records and generates and uploads the report for
	WellDyne

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('monolith_claims_timeout'):
		return True

	# Catch any exceptions
	try:

		# Get the timeout from the config
		iTimeout = Conf.get(('services', 'monolith', 'claims_timeout'), 172800)

		# Generate the date minus the timeout
		sDT = arrow.get().shift(seconds=-iTimeout).format('YYYY-MM-DD HH:mm:ss')

		# Find any Claims older than this date
		lClaims = CustomerClaimed.filter({
			"updatedAt": {"lte": sDT}
		})

		# Delete them all
		for o in lClaims:
			o.delete()

		# Return OK
		return True

	# Catch any error and email it
	except Exception as e:
		sBody = '%s\n\n%s' % (
			', '.join([str(s) for s in e.args]),
			traceback.format_exc()
		)
		emailError('Claim Timeout Cron Failed', sBody)
		return False
