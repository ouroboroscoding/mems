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
from RestOC import Conf, Record_MySQL

# Shared imports
from shared import Excel

# Cron imports
from . import isRunning

def _emailError(error):
	"""Email Error

	Send out an email with an error message

	Arguments:
		error (str): The error to email

	Returns:
		bool
	"""

	# Send the email
	oEff = Services.create('communications', 'email', {
		"_internal_": Services.internalKey(),
		"text_body": error,
		"subject": 'WellDyne Incoming Failed',
		"to": Conf.get(('developer', 'emails'))
	})
	if oEff.errorExists():
		print(oEff.error)
		return False

	# Return OK
	return True

def outbound_failed_claims(type):
	"""Outbound Failed Claims

	Lists triggered claims that have failed for some reason

	Arguments:
		type (str): Is it the morning or afternoon report?

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('wd_outbound_failed_claims'):
		return True

	# If type is invalid
	if type not in ['morning', 'afternoon']:
		print('Invalid type: %s' % type)
		return False

	# Get the day
	sDay = arrow.now().format('MMDDYY')

	# Get the sFTP and temp file conf
	dConf = Conf.get(('welldyne', 'sftp'))
	sTemp = Conf.get(('temp_folder'))

	# Generate the name of the file
	sFilename = 'MaleExcel_OutboundFailedClaims_%s%s.xlsx' % (
		sDay,
		type == 'afternoon' and '_3PM Report' or ''
	)

	# Connect to the sFTP
	with pysftp.Connection(**dConf) as oCon:

		# Get the outreach file
		try:
			sGet = '%s/%s' % (sTemp, sFilename)
			oCon.get(sFilename, sGet)
			#oCon.rename(sFilename, 'processed/%s' % sFilename)
		except FileNotFoundError:
			_emailError('%s file not found on sFTP' % sFilename)
			return False

	# Parse the data
	lData = Excel.parse(sGet, {
		"customerId": {"column": 10, "type": Excel.STRING},
		"queue": {"column": 0, "type": Excel.STRING},
		"reason": {"column": 14, "type": Excel.STRING},
		"exception": {"column": 17, "type": Excel.STRING},
		"rx": {"column": 15, "type": Excel.INTEGER}
	}, start_row=1)




def run(type, arg1=None):
	"""Run

	Entry point into the script

	Arguments:
		type (str): The type of report to parse
		arg1 (str): Possible data passed to the report

	Returns:
		int
	"""

	# If no type send, assume morning
	if not arg1:
		arg1 = 'morning'

	# Outbound failed claims
	if type == 'outbound':
		return (not outbound_failed_claims(arg1)) and 1 or 0

	# Opened claims
	elif type == 'opened':
		return (not opened_claims(arg1)) and 1 or 0

	# Got an invalid report
	print('Invalid report type: %s' % type)
	return 1
