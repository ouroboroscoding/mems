# coding=utf8
"""Customer Reviews

Fetches new customer review answers from MIP and stores them by customer so that
we have the last review as well as the average
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-07-19"

# Record imports
from records.monolith import CustomerReviews, TfAnswer
from records.reports import LastRun

# Cron imports
from crons import isRunning

# Defines
CRON_NAME = 'monolith_customer_reviews'

def run():
	"""Run

	Fetches all the reviews since the last run and updates the totals

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning(CRON_NAME):
		return True

	# Get the last ID processed
	oLastRun = LastRun.get(CRON_NAME)

	# Fetch all the new reviews
	lReviews = TfAnswer.reviewWithCustomerId(oLastRun['ts'])

	# Go through each one found
	for d in lReviews:

		# If there's no customer ID, skip it
		if not d['ktCustomerId']:
			continue

		# Add/update the customer review record
		CustomerReviews.addReview(int(d['ktCustomerId'], 0), int(d['review'], 0))

		# Update the last ID
		oLastRun['ts'] = d['id']
		oLastRun.save()

	# Return OK
	return True
