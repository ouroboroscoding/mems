# coding=utf8
"""Weekly Stats

Generates stats for the previous week for each agent group and user
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
		oSunday = arrow.get(datetime(*lDate), 'US/Eastern')
		oSaturday = oSunday.shift(days=6).ceil('day')

	# Else, get the previous week
	else:
		oSunday, oSaturday = arrow.get().to('US/Eastern').shift(weeks=-1).span('week', week_start=7)

	# Get and store all the counts by the range
	getAndStore(
		'week',
		oSunday.format('YYYY-MM-DD'),
		oSunday.int_timestamp,
		oSaturday.int_timestamp
	)
