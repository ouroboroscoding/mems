# coding=utf8
"""Daily Stats

Generates stats for the previous day for each agent group and user
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
		oYesterday = arrow.get(datetime(*lDate), 'US/Eastern')

	# Else, get yesterday's date
	else:
		oYesterday = arrow.now('US/Eastern').shift(days=-1)

	# Get and store all the counts by the range
	getAndStore(
		'day',
		oYesterday.format('YYYY-MM-DD'),
		oYesterday.floor('day').int_timestamp,
		oYesterday.ceil('day').int_timestamp
	)
