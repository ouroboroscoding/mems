# coding=utf8
"""Eligibility

Generates the WellDyne eligibility file and uploads it
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-05"

# Local imports
from crons.pharmacy_fill import WellDyne

def run(period=None):
	"""Run

	Generates eligibility and uploads it

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	# If we're doing the early morning run
	if period == 'morning':
		sFileTime = '043000'

	# Else, if we're doing the mid day run
	elif period == 'noon':
		sFileTime = '130000'

	# Else, invalid time period
	else:
		print('Invalid time period: %s' % time)
		return False

	# Regenerate the eligibility
	WellDyne.eligibilityUpload(sFileTime)

	# Return OK
	return True
