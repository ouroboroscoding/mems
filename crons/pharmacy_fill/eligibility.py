# coding=utf8
"""Pharmacy Fill

Generates the proper reports for pharmacies to fill new and recurring orders
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-02-04"

# Cron imports
from crons import emailError, isRunning

# Local imports
from . import WellDyne

def run(period=None):
	"""Run

	Fetches all transactions, outbound, and fill errors for the given time
	period and generates the appropriate pharmacy files for records

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	# If we're already running
	if isRunning('eligibility_%s' % period):
		return True

	try:

		# If we're doing the early morning run
		if period == 'morning':
			sFileTime = '043000'

		# Else, if we're doing the mid day run
		elif period == 'noon':
			sFileTime = '130000'

		else:
			print('Invalid time period: %s' % str(period))
			return False

		# Regenerate the eligibility
		WellDyne.eligibilityUpload(sFileTime)

	# Catch any error and email it
	except Exception as e:
		sBody = '%s\n\n%s' % (
			', '.join([str(s) for s in e.args]),
			traceback.format_exc()
		)
		emailError('Eligibility Failed', sBody)
		return False
