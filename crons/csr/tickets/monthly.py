# coding=utf8
"""Monthly Stats

Generates stats for the previous month for each agent group and user
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-06-10"

# Python imports
from datetime import datetime

# Pip imports
import arrow

# Local includes
from . import getAndStore

def run(date=None):
	"""Run

	Fetches all the stats for and stores them in the DB

	Arguments:
		date (str): Optional, used to override the date if necessary

	Returns:
		bool
	"""

	# If we have a date
	if date:
		lDate = [int(s, 10) for s in date.split('-')]
		oFirst, oLast = arrow.get(datetime(lDate[0], lDate[1], 1), 'US/Eastern').span('month')

	# Else, get the previous week
	else:
		oFirst, oLast = arrow.get().to('US/Eastern').shift(months=-1).span('month')

	# Get and store all the counts by the range
	getAndStore(
		'month',
		oFirst.format('YYYY-MM-DD'),
		oFirst.int_timestamp,
		oLast.int_timestamp
	)
