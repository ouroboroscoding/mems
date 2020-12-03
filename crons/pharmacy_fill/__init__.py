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

# Python imports
import traceback

# Pip imports
import arrow
from RestOC import Services

# Service imports
from services.konnektive import Konnektive
from records.prescriptions import PharmacyFill as FillRecord, PharmacyFillError
from records.welldyne import NeverStarted, Outbound

# Cron imports
from crons import emailError, isRunning
from crons.shared import PharmacyFill

# Local imports
from . import WellDyne, Generic

__moTriggers = None
"""Triggers file"""

__mdReports = None
"""Email reports"""

def _fill():
	"""Fill

	Fetches the manual fills and processes them

	Returns:
		list
	"""

	print('Fetching Pharmacy Fill')

	# Fetch all the manual fills
	lFills = FillRecord.get()

	# Go through each record
	for o in lFills:

		print('\tWorking on %s...' % o['crm_id'])

		# Try to process it
		dRes = PharmacyFill.process({
			"crm_type": o['crm_type'],
			"crm_id": o['crm_id'],
			"crm_order": o['crm_order']
		})

		# If we get success
		if dRes['status']:

			# Go through each medication returned
			for dData in dRes['data']:

				# If the pharmacy is Castia/WellDyne
				if dData['pharmacy'] in ['Castia', 'WellDyne']:

					# Add it to the Trigger
					__moTriggers.add(dData)

				# Else, add it to a generic pharmacy file
				else:

					# If it's a refill
					if dData['type'] == 'refill':

						# If we don't have the pharmacy
						if dData['pharmacy'] not in __mdReports:
							__mdReports[dData['pharmacy']] = Generic.EmailFile()

						# Add a line to the report
						__mdReports[dData['pharmacy']].add(dData)

		# Else, if it failed to process again
		else:

			# Create a new pharmacy fill error record
			oFillError = PharmacyFillError({
				"crm_type": o['crm_type'],
				"crm_id": o['crm_id'],
				"crm_order": o['crm_order'],
				"list": 'fill',
				"reason": dRes['data'][:255],
				"fail_count": 1
			})
			oFillError.create(conflict='replace')

	# Return the list to be deleted
	return lFills

def _fillErrors():
	"""Fill Errors

	Fetches the fill error records marked as ready and processes them

	Returns:
		list
	"""

	print('Fetching PharmacyFillError')

	# Init a list of the fills that will be deleted
	lErrorsToDelete = []

	# Fetch all previous fill / outbound error records that are ready to be
	#	re-processed
	lFillErrors = PharmacyFillError.filter({
		"list": ['fill', 'outbound'],
		"ready": True
	})

	# Go through each record
	for o in lFillErrors:

		print('\tWorking on %s...' % o['crm_id'])

		# Try to process it
		dRes = PharmacyFill.process({
			"crm_type": o['crm_type'],
			"crm_id": o['crm_id'],
			"crm_order": o['crm_order']
		})

		# If we get success
		if dRes['status']:

			# Go through each medication returned
			for dData in dRes['data']:

				# If it's a fill
				if o['list'] == 'fill':

					# If the pharmacy is Castia/WellDyne
					if dData['pharmacy'] in ['Castia', 'WellDyne']:

						# Add it to the Trigger
						__moTriggers.add(dData)

					# Else, add it to a generic pharmacy file
					else:

						# If it's a refill
						if dData['type'] == 'refill':

							# If we don't have the pharmacy
							if dData['pharmacy'] not in __mdReports:
								__mdReports[dData['pharmacy']] = Generic.EmailFile()

							# Add a line to the report
							__mdReports[dData['pharmacy']].add(dData)

				# Else, if it's an outbound
				elif o['list'] == 'outbound':

					# Overwrite the type and rx
					dData['type'] = 'update'
					dData['rx'] = o['wd_rx']

					# If the pharmacy is Castia/WellDyne
					if dData['pharmacy'] not in ['Castia', 'WellDyne']:
						emailError('WELLDYNE PHARMACY SWITCH', str(o.record()))
						continue

					# Add it to the Trigger
					__moTriggers.add(dData)

					# Add it to the outbound sent
					OutboundSent.fromFillError(o)

			# Add it to the delete list
			lErrorsToDelete.append(o)

		# Else, if it failed to process again
		else:

			# Increment the fail count, overwrite the reason, and reset the
			#	ready flag
			o['fail_count'] += 1
			o['reason'] = dRes['data']
			o['ready'] = False
			o.save();

	# Return the records that can be deleted
	return lErrorsToDelete

def _transactions(period):
	"""Transactions

	Fetches the Konnektive transactions and processes them

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		None
	"""

	# Create and init the Konnektive service
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
		print('Invalid time period: %s' % period)
		return False

	# Go through each type, CAPTURE and SALE
	for sTxnType in ['CAPTURE','SALE']:

		print('Fetching %s' % sTxnType)

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

			print('\tWorking on %d...' % d['customerId'])

			# Try to process it
			dRes = PharmacyFill.process({
				"crm_type": 'knk',
				"crm_id": str(d['customerId']),
				"crm_order": d['orderId']
			})

			# If we get success
			if dRes['status']:

				# Go through each medication returned
				for dData in dRes['data']:

					# If the pharmacy is Castia/WellDyne
					if dData['pharmacy'] in ['Castia', 'WellDyne']:

						# Add it to the Trigger
						__moTriggers.add(dData)

					# Else, add it to a generic pharmacy file
					else:

						# If it's a refill
						if dData['type'] == 'refill':

							# If we don't have the pharmacy
							if dData['pharmacy'] not in __mdReports:
								__mdReports[dData['pharmacy']] = Generic.EmailFile()

							# Add a line to the report
							__mdReports[dData['pharmacy']].add(dData)

			# Else, if the process failed
			else:

				# Create a new pharmacy fill error record
				oFillError = PharmacyFillError({
					"crm_type": 'knk',
					"crm_id": str(d['customerId']),
					"crm_order": d['orderId'],
					"list": 'fill',
					"reason": dRes['data'][:255],
					"fail_count": 1
				})
				oFillError.create(conflict='replace')

def _welldyneNeverStarted():
	"""Wedlldyne Never Started

	Fetches the never started records marked as ready and processes them

	Returns:
		list
	"""

	print('Fetching Never Started')

	# Fetch all the never started claims that are ready to be reprocessed
	lNeverStarted = NeverStarted.withTrigger({
		"ready": True
	})

	# Go through each record
	for d in lNeverStarted:

		print('\tWorking on %s...' % d['crm_id'])

		# Try to process it
		dRes = PharmacyFill.process({
			"crm_type": d['crm_type'],
			"crm_id": d['crm_id'],
			"crm_order": d['crm_order']
		})

		# If we get success
		if dRes['status']:

			# Go through each medication returned
			for dData in dRes['data']:

				# If the medications don't match, skip it
				if dData['medication'] != d['medication']:
					emailError('WELLDYNE MEDICATION MISMATCH', str(d))
					continue

				# If the pharmacy is not Castia/WellDyne
				if dData['pharmacy'] not in ['Castia', 'WellDyne']:
					emailError('WELLDYNE PHARMACY SWITCH', str(d))
					continue

				# Add it to the Trigger
				__moTriggers.add(dData, d['trigger_id'])

		# Else, if it failed to process again
		else:

			# Create a new pharmacy fill error record
			oFillError = PharmacyFillError({
				"crm_type": d['crm_type'],
				"crm_id": d['crm_id'],
				"crm_order": d['crm_order'],
				"list": 'fill',
				"reason": dRes['data'][:255],
				"fail_count": 1
			})
			oFillError.create(conflict='replace')

	# Return the list to be deleted
	return lNeverStarted

def _welldyneOutbound():
	"""WellDyne Outbound

	Fetches the outbound records marked as ready and processes them

	Returns:
		None
	"""

	print('Fetching Outbound')

	# Init a list of the outbound to be moved
	lOutboundToMove = []

	# Fetch all the outbound failed claims that are ready to be reprocessed
	lOutbound = Outbound.filter({
		"ready": True
	})

	# Go through each record
	for o in lOutbound:

		print('\tWorking on %s...' % o['crm_id'])

		# Try to process it
		dRes = PharmacyFill.process({
			"crm_type": o['crm_type'],
			"crm_id": o['crm_id'],
			"crm_order": o['crm_order']
		})

		# If we get success
		if dRes['status']:

			# Go through each medication returned
			for dData in dRes['data']:

				# Overwrite the type and rx
				dData['type'] = 'update'
				dData['rx'] = o['wd_rx']

				# If the pharmacy is not Castia/WellDyne
				if dData['pharmacy'] not in ['Castia', 'WellDyne']:
					emailError('WELLDYNE PHARMACY SWITCH', str(o.record()))
					continue

				# Add it to the Trigger
				__moTriggers.add(dData)

			# Add it to the list
			lOutboundToMove.append(o)

		# Else, if the process failed
		else:

			# Create a new pharmacy fill error record
			oFillError = PharmacyFillError({
				"crm_type": o['crm_type'],
				"crm_id": o['crm_id'],
				"crm_order": o['crm_order'],
				"list": 'outbound',
				"reason": dRes['data'][:255],
				"fail_count": 1
			})
			oFillError.create(conflict='replace')

			# Delete the outbound
			o.delete()

	# Return the list to move
	return lOutboundToMove

def run(period=None):
	"""Run

	Fetches all transactions, outbound, and fill errors for the given time
	period and generates the appropriate pharmacy files for records

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	global __moTriggers, __moKnk, __mdReports

	# If we're already running
	if isRunning('pharmacy_fill_%s' % period):
		return True

	try:

		# If we're doing the early morning run
		if period == 'morning':
			sFileTime = '043000'
			sEmailFile = '04:00:00'

		# Else, if we're doing the mid day run
		elif period == 'noon':
			sFileTime = '130000'
			sEmailFile = '12:30:00'

		else:
			print('Invalid time period: %s' % str(period))
			return False

		# Init the PharmacyFill module
		PharmacyFill.initialise()

		# Create a new instance of the WellDyne Trigger File
		__moTriggers = WellDyne.TriggerFile()

		# Create a list of generic pharmacies we email reports to
		__mdReports = {}

		# Run the transactions
		_transactions(period)

		# Run the manual fills
		lFills = _fill()

		# Run the outbound
		lOutboundToMove = _welldyneOutbound()

		# Run the never started
		lNeverStarted = _welldyneNeverStarted()

		# Run the pharmacy fill errors
		lErrorsToDelete = _fillErrors()

		# Upload the WellDyne trigger file
		__moTriggers.upload(sFileTime)

		# Go through each of the generic pharmacy emails
		for sPharmacy,oEmail in __mdReports.items():

			# Send the email
			oEmail.send(sPharmacy, sEmailFile)

		# Regenerate the eligibility
		WellDyne.eligibilityUpload(sFileTime)

		# Go through the outbound to move to sent
		for o in lOutboundToMove:
			o.sent()

		# Delete the never started
		if lNeverStarted:
			NeverStarted.deleteGet(
				[d['_id'] for d in lNeverStarted]
			)

		# Go through each fill and fill error that can be deleted
		if lFills:
			FillRecord.deleteGet(
				[o['_id'] for o in lFills]
			)
		if lErrorsToDelete:
			PharmacyFillError.deleteGet(
				[o['_id'] for o in lErrorsToDelete]
			)

		# Return OK
		return True

	# Catch any error and email it
	except Exception as e:
		sBody = '%s\n\n%s' % (
			', '.join([str(s) for s in e.args]),
			traceback.format_exc()
		)
		emailError('Pharmacy Fill Failed', sBody)
		return False
