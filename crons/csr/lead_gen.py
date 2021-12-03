# coding=utf8
"""Lead Gen

Generates a list of possible customers for upsells with either HRT or ED
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-11-09"

# Python imports
from pprint import pprint
import traceback

# Pip imports
import arrow
from RestOC import Conf, DateTimeHelper, Services, Sesh

# Service imports
from services.konnektive import Konnektive

# Record imports
from records.csr import Lead
from records.monolith import Campaign, CustomerReviews, HrtPatient, \
								KtOrderContinuous, TfAnswer, TfLanding

# Cron imports
from crons import emailError, isRunning

# Global vars
_campaigns = None
_knk = None

def _orderCounts(customer_id):
	"""Order Counts

	Fetches all orders for the customer and generates a count per campaign

	Arguments:
		customer_id (uint): The customer's unique ID

	Returns:
		dict
	"""

	# Init the return
	dRet = {
		"ed": 0,
		"concierge": 0,
		"itemized": 0
	}

	# Fetch all orders for this customer from KNK
	lOrders = _knk._request('order/query', {
		"customerId": customer_id,
		"orderStatus": 'COMPLETE'
	})

	# Go through each order
	for d in lOrders:

		# If the campaign is itemized med orders
		if d['campaignId'] in [123, 138]:

			# If we have a concierge fee item
			if 'items' in d and '860' in d['items']:
				dRet['concierge'] += 1

			# Else, it's products
			else:
				dRet['itemized'] += 1

		# Else, if the campaign is ed
		if d['campaignId'] in _campaigns and _campaigns[d['campaignId']] == 'ed':
				dRet['ed'] += 1

	# Return the counts
	return dRet

def _processED(customer_id, counts):
	"""Process ED

	Check if an ED patient is eligble to be setup as a lead for HRT/other meds

	Arguments:
		customer_id (uint): The unique ID of the customer
		counts: (dict): The counts of order/product types for the customer

	Returns:
		None
	"""

	# If the customer has less than 12 ED orders, skip them for now
	if counts['ed'] < 12:
		return

	# If they have even one concierge fee
	if counts['concierge']:

		# Mark the patient as being both ED and HRT so we skip them next
		#	time
		oLead = Lead({
			"customerId": customer_id,
			"status": 'ignore',
			"type": 'current',
			"medications": Lead.MEDICATION_ED | Lead.MEDICATION_HRT
		})
		oLead.create()
		return

	# Get the DOB of the customer
	oResponse = Services.read('monolith', 'customer/dob', {
		"_internal_": Services.internalKey(),
		"customerId": str(customer_id)
	})

	# If there's no DOB just skip for now
	if oResponse.errorExists() or oResponse.data == False:
		return

	# Get the age from the DOB
	iAge = DateTimeHelper.age(oResponse.data)

	# If the customer is over 70
	if iAge >= 70:

		# Mark the patient as ED but skip them next time
		oLead = Lead({
			"customerId": customer_id,
			"status": 'ignore',
			"type": 'current',
			"medications": Lead.MEDICATION_ED
		})
		oLead.create()
		return

	# If they're under 45, skip for now
	if iAge < 45:
		return

	# Customer passed all checks, add them as an ED customer that can
	#	potentially be upsold
	oLead = Lead({
		"customerId": customer_id,
		"status": 'added',
		"type": 'current',
		"medications": Lead.MEDICATION_ED
	})
	oLead.create()

def _processHRT(customer_id, counts):
	"""Process HRT

	Check if an HRT patient is eligble to be setup as a lead for ED/other meds

	Arguments:
		customer_id (uint): The unique ID of the customer
		counts: (dict): The counts of order/product types for the customer

	Returns:
		None
	"""

	# If the customer has less than 3 itemized orders, skip them for now
	if counts['itemized'] < 3:
		return

	# If there's any ED at all
	if counts['ed']:

		# Mark the patient as being both ED and HRT so we skip them next
		#	time
		oLead = Lead({
			"customerId": customer_id,
			"status": 'ignore',
			"type": 'current',
			"medications": Lead.MEDICATION_ED | Lead.MEDICATION_HRT
		})
		oLead.create()
		return

	# Search for ratings
	dReviews = CustomerReviews.get(customer_id)

	# If we have none, or it's under 8, skip for now
	if not dReviews or dReviews['last'] < 8:
		return

	# Get the latest completed HRT landing (MIP)
	dLanding = TfLanding.filter({
			"complete": 'Y',
			"ktCustomerId": str(customer_id),
			"formId": ['MIP-H1', 'MIP-H2']
		},
		raw=['landing_id'],
		orderby=[['submitted_at', 'DESC']],
		limit=1
	)

	# Find any low libido answer associated with the landing
	dAnswer = TfAnswer.filter({
		"landing_id": dLanding['landing_id'],
		"ref": ['lowLibido', 'low_libido']
	}, raw=['value'], limit=1)

	# If there's no answer, or it's '0', skip them for now
	if not dAnswer or dAnswer['value'] == '0':
		return

	# Customer passed all checks, add them as an HRT customer that can
	#	potentially be upsold
	oLead = Lead({
		"customerId": customer_id,
		"status": 'added',
		"type": 'current',
		"medications": Lead.MEDICATION_HRT
	})
	oLead.create()

def _transactions():
	"""Transactions

	Fetches the Konnektive transactions for the previous day and processes them

	Returns:
		None
	"""

	# Import globals
	global _campaigns, _knk

	# Fetch all the campaigns and store the type by ID
	_campaigns = {
		d['id']:d['type']
		for d in Campaign.get(raw=['id', 'type'])
	}

	# Create and init the Konnektive service
	_knk = Konnektive()
	_knk.initialise()

	# Generate the date
	sDate = arrow.get().shift(days=-1).format('MM/DD/YYYY')

	# Fetch the successfull sales transactions from Konnektive
	lTransactions = _knk._request('transactions/query', {
		"responseType": "SUCCESS",
		"txnType": 'SALE',
		"startDate": sDate,
		"startTime": '00:00:00',
		"endDate": sDate,
		"endTime": '23:59:59'
	});

	# Go through each transaction
	for d in lTransactions:

		# Do we already have the customer in lead gen?
		if Lead.exists(d['customerId']):
			continue;

		# Get the order counts
		dCounts = _orderCounts(d['customerId'])
		#print('----------------------------------------')
		#print('customerId: %d' % d['customerId'])
		#print('counts: ', end='')
		#pprint(dCounts)

		# Convert campaign to int
		d['campaignId'] = int(d['campaignId'], 10)

		# If the campaign doesn't exist
		if d['campaignId'] not in _campaigns:
			emailError('Lead Gen Issue', 'Unknown campaign: %d' % d['campaignId'])
			continue

		# If the transaction is in an ED campaign
		if _campaigns[d['campaignId']] == 'ed':
			_processED(d['customerId'], dCounts)

		# Else, if the transaction is in an HRT campaign
		elif _campaigns[d['campaignId']] == 'hrt':
			_processHRT(d['customerId'], dCounts)

def run():
	"""Run

	Entry point of the script

	Returns:
		bool
	"""

	# If we're already running
	if isRunning('csr_lead_gen'):

		# Notify dev of a possible issue
		emailError('Lead Gen Issue', 'Lead gen still running after 24hrs')
		return True

	# Fetch and process all the transactions
	_transactions()

	# Return OK
	return True
