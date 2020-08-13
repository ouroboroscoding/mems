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
from records.prescriptions import PharmacyFillError
from records.welldyne import Outbound

# Cron imports
from crons import emailError, isRunning
from crons.shared import PharmacyFill

# Local imports
from . import WellDyne, Generic

def run(period=None):
	"""Run

	Fetches all transactions, outbound, and fill errors for the given time
	period and generates the appropriate pharmacy files for records

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	try:

		# Init the PharmacyFill module
		PharmacyFill.initialise()

		# Create a new instance of the WellDyne Trigger File
		oTrigger = WellDyne.TriggerFile()

		# Create a list of generic pharmacies we email reports to
		dReports = {}

		# Init the Konnektive service
		oKnk = Konnektive()
		oKnk.initialise()

		# If we're doing the early morning run
		if period == 'morning':
			sStartDate = arrow.get().shift(days=-1).format('MM/DD/YYYY')
			sStartTime = '12:30:00'
			sEndDate = arrow.get().format('MM/DD/YYYY')
			sEndTime = '03:59:59'
			sFileTime = '043000'

		# Else, if we're doing the mid day run
		elif period == 'noon':
			sStartDate = arrow.get().format('MM/DD/YYYY')
			sStartTime = '04:00:00'
			sEndDate = sStartDate
			sEndTime = '12:29:59'
			sFileTime = '130000'

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
							oTrigger.add(dData)

						# Else, add it to a generic pharmacy file
						else:

							# If it's a refill
							if dData['type'] == 'refill':

								# If we don't have the pharmacy
								if dData['pharmacy'] not in dReports:
									dReports[dData['pharmacy']] = Generic.EmailFile()

								# Add a line to the report
								dReports[dData['pharmacy']].add(dData)

				# Else, if the process failed
				else:

					# Create a new pharmacy fill error record
					oFillError = PharmacyFillError({
						"crm_type": 'knk',
						"crm_id": str(d['customerId']),
						"crm_order": d['orderId'],
						"list": 'fill',
						"type": '',
						"reason": dRes['data'],
						"fail_count": 1
					})
					oFillError.create(conflict='replace')

		print('Fetching Outbound')

		# Fetch all the outbound failed claims that are ready to be reprocessed
		lOutbound = Outbound.filter({
			"ready": True
		})

		# Go through each record
		for o in lOutbound:

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

					# If the pharmacy is Castia/WellDyne
					if dData['pharmacy'] not in ['Castia', 'WellDyne']:
						emailError('WELLDYNE PHARMACY SWITCH', str(o.record()))
						continue

					# Add it to the Trigger
					oTrigger.add(dData)

				# Move it to the sent table
				o.sent()

			# Else, if the process failed
			else:

				# Create a new pharmacy fill error record
				oFillError = PharmacyFillError({
					"crm_type": 'knk',
					"crm_id": str(d['customerId']),
					"crm_order": d['orderId'],
					"list": 'outbound',
					"type": '',
					"reason": dRes['data'],
					"fail_count": 1
				})
				oFillError.create(conflict='replace')

		print('Fetching PharmacyFillError')

		# Fetch all previous fill / outbound error records that are ready to be
		#	re-processed
		lFillErrors = PharmacyFillError.filter({
			"list": ['fill', 'outbound'],
			"ready": True
		})

		# Go through each record
		for o in lFillErrors:

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
							oTrigger.add(dData)

						# Else, add it to a generic pharmacy file
						else:

							# If it's a refill
							if dData['type'] == 'refill':

								# If we don't have the pharmacy
								if dData['pharmacy'] not in dReports:
									dReports[dData['pharmacy']] = Generic.EmailFile(sEndTime)

								# Add a line to the report
								dReports[dData['pharmacy']].add(dData)

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
						oTrigger.add(dData)

						# Add it to the outbound sent
						OutboundSent.fromFillError(o)

				# Delete it
				o.delete()

			# Else, if it failed to process again
			else:

				# Increment the fail count, overwrite the reason, and reset the
				#	ready flag
				o['fail_count'] += 1
				o['reason'] = dRes['data']
				o['ready'] = False
				o.save();

		# Upload the WellDyne trigger file
		oTrigger.upload(sFileTime)

		# Go through each of the generic pharmacy emails
		for sPharmacy,oEmail in dReports.items():

			# Send the email
			oEmail.send(sPharmacy, sEndTime)

		# Regenerate the eligibility
		WellDyne.eligibilityUpload(sFileTime)

		# If we have any expiring soon
		if PharmacyFill._mlExpiring:

			# Generate the email body
			sBody = '%s<br />%s' % (
				'<strong>ID, Order, RX#</strong>',
				'<br />'.join(['%s, %s, %d' % (
					d['crm_id'], d['crm_order'], d['ds_id']
				) for d in PharmacyFill._mlExpiring])
			)

			# Send the email
			oEff = Services.create('communications', 'email', {
				"_internal_": Services.internalKey(),
				"html_body": sBody,
				"subject": 'Prescriptions expiring soon',
				"to": "ew@maleexcel.com"
			})
			if oEff.errorExists():
				print(oEff.error)

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
