# coding=utf8
"""Pharmacy Fill

Generates the proper reports for pharmacies to fill new and recurring orders
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-01"

# Pip imports
import arrow

# Service imports
from services.konnektive import Konnektive
from services.welldyne import WellDyne

# Cron imports
from crons import isRunning
from crons.shared import PharmacyFill
from crons.shared.WdTriggerFile import WdTriggerFile

def eligibility_test():

	# If the script already running?
	if isRunning('eligibility_test'):
		return True

	WellDyne._eligibilityGenerateAndUpload('043000')
	return True


def run(period=None):
	"""Transactions

	Fetches all transactions for the given time period and generates the
	appropriate pharmacy files for records

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	# Init the PharmacyFill module
	PharmacyFill.initialise()

	# Init the Konnektive service
	oKnk = Konnektive()
	oKnk.initialise()

	# If we're doing the early morning run
	if period == 'morning':
		sStartDate = arrow.get().shift(days=-1).format('MM/DD/YYYY')
		sStartTime = '12:30:00'
		sEndDate = arrow.get().format('MM/DD/YYYY')
		sEndTime = '03:59:59'

	# Else, if we're doing the mid day run
	elif period == 'noon':
		sStartDate = arrow.get().format('MM/DD/YYYY')
		sStartTime = '04:00:00'
		sEndDate = sStartDate
		sEndTime = '12:29:59'

	# Else, invalid time period
	else:
		print('Invalid time period: %s' % time)
		return False

	# Go through each type, CAPTURE and SALE
	for sTxnType in ['CAPTURE','SALE']:

		# Fetch the records from Konnektive
		lTransactions = oKnk._request('transactions/query', {
			"responseType": "SUCCESS",
			"txnType": sTxnType,
			"startDate": sStartDate,
			"startTime": sStartTime,
			"endDate": sEndDate,
			"endTime": sEndTime
		});

		# Go through each record
		for d in lTransactions:

			# If the campaign name contains HRT, skip it
			if 'HRT' in d['campaignName']:
				continue

			# Try to process it
			dRes = PharmacyFill.process({
				"crm_type": 'knk',
				"crm_id": d['customerId'],
				"crm_order": d['orderId']
			})

			# If we get success
			if dRes['status']:



				print(dRes['data'])
			else:
				print('%d, %s' % (d['customerId'], dRes['data']))
			print('-----------------------------------------------------')

	# Return OK
	return True
