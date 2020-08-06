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

# Pip imports
import arrow
import pysftp
from RestOC import Conf

# Shared imports
from shared import Excel, Memo

# Service imports
from services.welldyne.records import Outbound, RxNumber, Trigger

# Cron imports
from crons import isRunning, emailError

def opened_claims(time):
	"""Opened Claims

	Lists triggered claims that have been opened by WellDyneRX

	Arguments:
		time (str): Is it the morning or afternoon report?

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('wd_opened_triggers'):
		return True

	# If time is invalid
	if time not in ['morning', 'afternoon']:
		print('Invalid time: %s' % time)
		return False

	# Get the day
	sDay = arrow.now().format('MMDDYY')

	# Get the sFTP and temp file conf
	dConf = Conf.get(('welldyne', 'sftp'))
	sTemp = Conf.get(('temp_folder'))

	# Generate the name of the file
	sFilename = 'MaleExcel_DailyOpenedClaims_%s%s.xlsx' % (
		sDay,
		time == 'afternoon' and '_3PM Report' or ''
	)

	# Connect to the sFTP
	with pysftp.Connection(dConf['host'], username=dConf['username'], password=dConf['password']) as oCon:

		# Get the outreach file
		try:
			sGet = '%s/%s' % (sTemp, sFilename)
			oCon.get(sFilename, sGet)
			#oCon.rename(sFilename, 'processed/%s' % sFilename)
		except FileNotFoundError:
			emailError('WellDyne Incoming Failed', '%s file not found on sFTP' % sFilename)
			return False

	# Parse the data
	"""
	lData = Excel.parse(sGet, {
		"crm_id": {"column": 10, "type": Excel.STRING},
		"queue": {"column": 0, "type": Excel.STRING},
		"reason": {"column": 14, "type": Excel.STRING},
		"exception": {"column": 17, "type": Excel.STRING},
		"wd_rx": {"column": 15, "type": Excel.INTEGER}
	}, start_row=1)

	# Go through each item
	for d in lData:

		# Get the CRM ID
		sCrmID = d['crm_id'].lstrip('0')
	"""

	# Delete the file
	os.remove(sGet)

	# Return OK
	return True

def outbound_failed_claims(time):
	"""Outbound Failed Claims

	Lists triggered claims that have failed for some reason

	Arguments:
		time (str): Is it the morning or afternoon report?

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('wd_outbound_failed_claims'):
		return True

	# If time is invalid
	if time not in ['morning', 'afternoon']:
		print('Invalid time: %s' % time)
		return False

	# Get the day
	sDay = arrow.now().format('MMDDYY')

	# Get the sFTP and temp file conf
	dConf = Conf.get(('welldyne', 'sftp'))
	sTemp = Conf.get(('temp_folder'))

	# Generate the name of the file
	sFilename = 'MaleExcel_OutboundFailedClaims_%s%s.xlsx' % (
		sDay,
		time == 'afternoon' and '_3PM Report' or ''
	)

	# Connect to the sFTP
	with pysftp.Connection(dConf['host'], username=dConf['username'], password=dConf['password']) as oCon:

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
		"crm_id": {"column": 10, "type": Excel.STRING},
		"queue": {"column": 0, "type": Excel.STRING},
		"reason": {"column": 14, "type": Excel.STRING},
		"exception": {"column": 17, "type": Excel.STRING},
		"wd_rx": {"column": 15, "type": Excel.INTEGER}
	}, start_row=1)

	# Go through each item
	for d in lData:

		# If we got no ID
		if not d['crm_id']:
			emailError('OUTBOUND FAILED', str(d))
			continue

		# Get the CRM ID
		sCrmID = d['crm_id'].lstrip('0')

		# Find the last trigger associated with the ID
		dTrigger = Trigger.filter({
			"crm_type": 'knk',
			"crm_id": sCrmID,
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

def shipped_claims(time):
	"""Shipped Claims

	Lists triggered claims that have been shipped

	Arguments:
		time (str): Is it the morning or afternoon report?

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('wd_daily_shipped'):
		return True

	# If time is invalid
	if time not in ['morning', 'afternoon']:
		print('Invalid time: %s' % time)
		return False

	# Get the day
	sDay = arrow.now().format('MMDDYY')

	# Get the sFTP and temp file conf
	dConf = Conf.get(('welldyne', 'sftp'))
	sTemp = Conf.get(('temp_folder'))

	# Generate the name of the file
	sFilename = 'MaleExcel_DailyShippedOrders_%s%s.xlsx' % (
		sDay,
		time == 'afternoon' and '_3PM Report' or ''
	)

	# Connect to the sFTP
	with pysftp.Connection(dConf['host'], username=dConf['username'], password=dConf['password']) as oCon:

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
		"shipped": {"column": 1, "type": Excel.DATETIME},
		"tracking": {"column": 3, "type": Excel.STRING},
		"rx": {"column": 7, "type": Excel.INTEGER},
		"member_id": {"column": 17, "type": Excel.STRING}
	}, start_row=1)

	# Go through each item
	for d in lData:

		# Get the CRM ID
		sCrmID = d['member_id'].lstrip('0')

		# Find the last trigger associated with the ID
		oTrigger = Trigger.filter({
			"crm_type": 'knk',
			"crm_id": sCrmID,
		}, orderby=[('_created', 'DESC')], limit=1)

		# If we found one
		if oTrigger:

			# Update the shipped date
			oTrigger['shipped'] = d['shipped']

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

		# Send the tracking to Memo
		dRes = Memo.create('rest/shipping', {
			"code": d['tracking'],
			"type": d['tracking'][0:2] == '1Z' and 'UPS' or 'USPS',
			"date": d['shipped'],
			"customerId": sCrmID
		})
		if dRes['error']:
			print(dRes['error'])

	# Delete the file
	os.remove(sGet)

	# Return OK
	return OK

def run(report, time=None):
	"""Run

	Entry point into the script

	Arguments:
		report (str): The type of report to parse
		time (str): The time of day of the report

	Returns:
		int
	"""

	# If no time sent, assume morning
	if not time:
		time = 'morning'

	# Opened claims
	if report == 'opened':
		return opened_claims(time)

	# Outbound failed claims
	elif report == 'outbound':
		return outbound_failed_claims(time)

	# Shipped claims
	elif report == 'shipped':
		return shipped_claims(time)

	# Got an invalid report
	print('Invalid welldyne incoming report: %s' % report)
	return 1
