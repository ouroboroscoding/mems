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
from records.csr import Agent
from records.monolith import CustomerClaimed

# Cron imports
from crons import emailError, isRunning

# Shared import
from shared import Sync

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

	# Init the sync module
	Sync.init()

	# Catch any exceptions
	try:

		# Get all agents
		lAgents = Agent.get(raw=['memo_id', 'claims_timeout'])

		# Create groups based on timeout length
		dTimeouts = {}
		for d in lAgents:
			try: dTimeouts[d['claims_timeout']].append(d['memo_id'])
			except: dTimeouts[d['claims_timeout']] = [d['memo_id']]

		# Go through each group
		for iHours,lAgents in dTimeouts.items():

			# Generate the date minus the timeout
			sDT = arrow.get().shift(hours=-iHours).format('YYYY-MM-DD HH:mm:ss')

			# Find any Claims older than this date
			lClaims = CustomerClaimed.filter({
				"user": lAgents,
				"updatedAt": {"lte": sDT}
			})

			# Go through each one
			for o in lClaims:

				# Notify the user they lost the claim
				Sync.push('monolith', 'user-%s' % str(o['user']), {
					"type": 'claim_removed',
					"phoneNumber": o['phoneNumber']
				})

				# Delete it
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
