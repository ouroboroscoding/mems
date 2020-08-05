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
from shared import Excel

# Service imports
from services.welldyne.records import Outbound, Trigger

# Cron imports
from crons import isRunning, emailError

def opened_triggers(time):
	"""Opened Triggers

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
	with pysftp.Connection(**dConf) as oCon:

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
	with pysftp.Connection(**dConf) as oCon:

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

		# Get the CRM ID
		sCrmID = d['crm_id'].lstrip('0')

		# Find the last trigger associated with the ID
		dTrigger = Trigger.filter({
			"crm_type": 'knk',
			"crm_id": sCrmID,
		}, raw=['crm_order'], orderby=(('_created', 'DESC')), limit=1)

		# Create the instance
		oOutbound = Outbound({
			"crm_type": 'knk',
			"crm_id": sCrmID,
			"crm_order": dTrigger['crm_order'],
			"queue": d['queue'],
			"reason": '%s %s' % (
				d['reason'] or '',
				d['exception'] or ''
			),
			"wd_rx": d['wd_rx'],
			"ready": False
		})

		# Create the record in the DB
		oOutbound.create(conflict='replace')

	# Return OK
	return True

def run(report, time=None):
	"""Run

	Entry point into the script

	Arguments:
		report (str): The type of report to parse
		time (str): The time of day of the report

	Returns:
		int
	"""

	# If no type send, assume morning
	if not time:
		time = 'morning'

	# Outbound failed claims
	if type == 'outbound':
		return (not outbound_failed_claims(time)) and 1 or 0

	# Opened claims
	elif type == 'opened':
		return (not opened_claims(time)) and 1 or 0

	# Got an invalid report
	print('Invalid welldyne incoming report: %s' % type)
	return 1
