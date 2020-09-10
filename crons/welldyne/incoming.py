# coding=utf8
"""WellDyneRX Incoming Reports

Parses incoming reports from WellDyneRX to place the data in the DB
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-07-29"

# Python imports
import os
import time

# Pip imports
import arrow
import pysftp
from RestOC import Conf

# Shared imports
from shared import Excel

# Service imports
from records.monolith import ShippingInfo
from records.welldyne import Outbound, RxNumber, Trigger

# Cron imports
from crons import isRunning, emailError
from crons.shared import SMSWorkflow

def opened_claims(tod):
	"""Opened Claims

	Lists triggered claims that have been opened by WellDyneRX

	Arguments:
		tod (str): Is it the morning or afternoon report?

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('wd_opened_triggers'):
		return True

	# If tod is invalid
	if tod not in ['morning', 'afternoon']:
		print('Invalid tod: %s' % tod)
		return False

	# Get the day
	sDay = arrow.now().format('MMDDYY')

	# Get the sFTP and temp file conf
	dSftpConf = Conf.get(('welldyne', 'sftp'))
	sTemp = Conf.get(('temp_folder'))

	# Generate the name of the file
	sFilename = 'MaleExcel_DailyOpenedClaims_%s%s.xlsx' % (
		sDay,
		tod == 'afternoon' and '_3PM Report' or ''
	)

	# Connect to the sFTP
	with pysftp.Connection(dSftpConf['host'], username=dSftpConf['username'], password=dSftpConf['password']) as oCon:

		# Get the outreach file
		try:
			sGet = '%s/%s' % (sTemp, sFilename)
			oCon.get(sFilename, sGet)
			#oCon.rename(sFilename, 'processed/%s' % sFilename)
		except FileNotFoundError:
			emailError('WellDyne Incoming Failed', '%s file not found on sFTP' % sFilename)
			return False

	# Parse the data
	lData = Excel.parse(sGet, {
		"member_id": {"column": 2, "type": Excel.STRING},
		"opened": {"column": 6, "type": Excel.DATETIME},
		"wd_rx": {"column": 7, "type": Excel.INTEGER},
		"stage": {"column": 13, "type": Excel.STRING},
		"queue": {"column": 15, "type": Excel.STRING}
	}, start_row=1)

	# Go through each one and keep only uniques
	dData = {}
	for d in lData:
		d['customerId'] = d['member_id'].lstrip('0')
		dData[d['customerId']] = d

	# Store just the values
	lData = list(dData.values())

	# Go through each item
	for d in lData:

		# Create the reason string
		sReason = '%s %s' % (d['queue'] or '', d['stage'] or '')

		# If it's empty
		if len(sReason) == 0 or sReason == ' ':
			sReason = '(empty)'

		# Find the last trigger associated with the ID
		oTrigger = Trigger.filter({
			"crm_type": 'knk',
			"crm_id": d['customerId'],
			"type": {"neq": 'update'}
		}, orderby=[('_created', 'DESC')], limit=1)

		# If we found one
		if oTrigger:

			# Update the opened date and stage
			oTrigger['shipped'] = d['opened']
			oTrigger['opened_stage'] = sReason

			# Save the updates
			oTrigger.save()

		# Create or replace the current RX number
		oRx = RxNumber({
			"member_id": d['member_id'],
			"number": d['rx']
		})
		oRx.create(conflict=['number'])

	# Delete the file
	os.remove(sGet)

	# Return OK
	return True

def outbound_failed_claims(tod):
	"""Outbound Failed Claims

	Lists triggered claims that have failed for some reason

	Arguments:
		tod (str): Is it the morning or afternoon report?

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('wd_outbound_failed_claims'):
		return True

	# If tod is invalid
	if tod not in ['morning', 'afternoon']:
		print('Invalid tod: %s' % tod)
		return False

	# Get the day
	sDay = arrow.now().format('MMDDYY')

	# Get the sFTP and temp file conf
	dSftpConf = Conf.get(('welldyne', 'sftp'))
	sTemp = Conf.get(('temp_folder'))

	# Generate the name of the file
	sFilename = 'MaleExcel_OutboundFailedClaims_%s%s.xlsx' % (
		sDay,
		tod == 'afternoon' and '_3PM Report' or ''
	)

	# Connect to the sFTP
	with pysftp.Connection(dSftpConf['host'], username=dSftpConf['username'], password=dSftpConf['password']) as oCon:

		# Get the outreach file
		try:
			sGet = '%s/%s' % (sTemp, sFilename)
			oCon.get(sFilename, sGet)
			oCon.rename(sFilename, 'processed/%s' % sFilename)
		except FileNotFoundError:
			emailError('WellDyne Incoming Failed', '%s file not found on sFTP' % sFilename)
			return False

	# Parse the data
	lData = Excel.parse(sGet, {
		"crm_id": {"column": 10, "type": Excel.STRING},
		"queue": {"column": 0, "type": Excel.STRING},
		"reason": {"column": 14, "type": Excel.STRING},
		"exception": {"column": 17, "type": Excel.STRING},
		"wd_rx": {"column": 15, "type": Excel.INTEGER}
	}, start_row=1)

	# Delete all current outbounds that aren't marked as ready
	Outbound.deleteNotReady()

	# Go through each item
	for d in lData:

		# If we got no ID
		if not d['crm_id']:
			emailError('OUTBOUND FAILED', str(d))
			continue

		# If all zeros, skip it
		if d['crm_id'] == '000000':
			continue

		# Get the CRM ID
		sCrmID = d['crm_id'].lstrip('0')

		# Find the last trigger associated with the ID
		dTrigger = Trigger.filter({
			"crm_type": 'knk',
			"crm_id": sCrmID,
			"type": {"neq": 'update'}
		}, raw=['crm_order'], orderby=[('_created', 'DESC')], limit=1)

		# Create the reason string
		sReason = '%s %s' % (d['reason'] or '', d['exception'] or '')

		# If it's empty
		if len(sReason) == 0 or sReason == ' ':
			sReason = '(empty)'

		# Create the instance
		oOutbound = Outbound({
			"crm_type": 'knk',
			"crm_id": sCrmID,
			"crm_order": dTrigger and dTrigger['crm_order'] or '',
			"queue": d['queue'] or '(empty)',
			"reason": sReason[:255],
			"wd_rx": d['wd_rx'] or '',
			"ready": False
		})

		# Create the record in the DB
		oOutbound.create(conflict='replace')

	# Delete the file
	os.remove(sGet)

	# Return OK
	return True

def shipped_claims(tod):
	"""Shipped Claims

	Lists triggered claims that have been shipped

	Arguments:
		tod (str): Is it the morning or afternoon report?

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('wd_daily_shipped'):
		return True

	# If tod is invalid
	if tod not in ['morning', 'afternoon']:
		print('Invalid tod: %s' % tod)
		return False

	# Get the day
	sDay = arrow.now().format('MMDDYY')

	# Get the sFTP and temp file conf
	dSftpConf = Conf.get(('welldyne', 'sftp'))
	sTemp = Conf.get(('temp_folder'))

	# Generate the name of the file
	sFilename = 'MaleExcel_DailyShippedOrders_%s%s.xlsx' % (
		sDay,
		tod == 'afternoon' and '_3PM Report' or ''
	)

	# Connect to the sFTP
	with pysftp.Connection(dSftpConf['host'], username=dSftpConf['username'], password=dSftpConf['password']) as oCon:

		# Get the outreach file
		try:
			sGet = '%s/%s' % (sTemp, sFilename)
			oCon.get(sFilename, sGet)
			oCon.rename(sFilename, 'processed/%s' % sFilename)
		except FileNotFoundError:
			emailError('WellDyne Incoming Failed', '%s file not found on sFTP' % sFilename)
			return False

	# Parse the data
	lData = Excel.parse(sGet, {
		"shipped": {"column": 1, "type": Excel.DATETIME},
		"tracking": {"column": 3, "type": Excel.STRING},
		"rx": {"column": 7, "type": Excel.INTEGER},
		"member_id": {"column": 17, "type": Excel.STRING}
	}, start_row=1)

	# Go through each one and keep only uniques
	dData = {}
	for d in lData:
		d['customerId'] = d['member_id'].lstrip('0')
		dData[d['customerId']] = d

	# Store just the values
	lData = list(dData.values())

	# Go through each item
	for d in lData:

		# Find the last trigger associated with the ID
		oTrigger = Trigger.filter({
			"crm_type": 'knk',
			"crm_id": d['customerId'],
			"type": {"neq": 'update'}
		}, orderby=[('_created', 'DESC')], limit=1)

		# If we found one
		if oTrigger:

			# Update the shipped date and clear the opened stage
			oTrigger['shipped'] = d['shipped']
			oTrigger['opened_state'] = ''

			# If there's no opened date, update it too
			if not oTrigger['opened']:
				oTrigger['opened'] = d['shipped']

			# Save the updates
			oTrigger.save()

		# Create or replace the current RX number
		oRx = RxNumber({
			"member_id": d['member_id'],
			"number": d['rx']
		})
		oRx.create(conflict=['number'])

		# Get the date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Create the shipping info
		try:
			dShipInfo = {
				"code": d['tracking'],
				"customerId": d['customerId'],
				"date": d['shipped'][0:10],
				"type": d['tracking'][0:2] == '1Z' and 'UPS' or 'USPS',
				"createdAt": sDT,
				"updatedAt": sDT
			}
			oShippingInfo = ShippingInfo(dShipInfo)
			bCreated = oShippingInfo.create(conflict="ignore")

			# If the record didn't exist, send an SMS
			if bCreated:
				SMSWorkflow.shipping(oShippingInfo.record())
		except ValueError as e:
			emailError('Welldyne Incoming Failed', 'Invalid shipping info: %s\n\n%s' % (
				str(e.args[0]),
				str(dShipInfo)
			))
			continue

	# Delete the file
	os.remove(sGet)

	# Return OK
	return True

def run(report, tod=None):
	"""Run

	Entry point into the script

	Arguments:
		report (str): The type of report to parse
		tod (str): The time of day of the report

	Returns:
		bool
	"""

	# If no tod sent, assume morning
	if not tod:
		tod = 'morning'

	# Opened claims
	if report == 'opened':
		return opened_claims(tod)

	# Outbound failed claims
	elif report == 'outbound':
		return outbound_failed_claims(tod)

	# Shipped claims
	elif report == 'shipped':
		return shipped_claims(tod)

	# Got an invalid report
	print('Invalid welldyne incoming report: %s' % report)
	return False
