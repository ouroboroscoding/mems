# coding=utf8
"""Missed Calls

Checks SG email for messages about missed calls
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-10"

# Python imports
from datetime import datetime
import imaplib

# Pip imports
from RestOC import Conf

# Service imports
from services.konnektive import Konnektive

# Shared imports
from shared import GSheets

# Cron imports
from crons import isRunning

# Local imports
from . import justcall, signia

_knk = Konnektive()

def get_customer(number):
	"""Get Customer

	Attempts to fetch the customer ID from konnektive

	Arguments:
		number (str): The customer's phone number

	Returns:
		str
	"""

	# Find the customer ID
	lRes = _knk._request('customer/query', {
		"startDate": '01/01/2000',
		"endDate": '01/01/3000',
		"phoneNumber": number,
		"sortDir": '0'
	})

	# Return if we found anything
	return len(lRes) and str(lRes[0]['customerId']) or ''

def process_default(conf, data):
	"""Process Default

	Process the default missed calls data and adds it to the CS logs

	Arguments:
		conf (dict): Key and worksheet name to write to
		data (dict[]): List of data to process

	Returns:
		None
	"""

	# Go through each item in the data
	for d in data:

		# Get the customer ID
		sCustID = get_customer(d['from'])

		# Set the CS tool url
		sCSR = sCustID and 'https://cs.meutils.com/view/%s/%s' % (d['from'], sCustID) or ''

		# Write to the worksheet
		GSheets.insert('sg', conf['key'], conf['worksheet'], [
			d['date'], d['time'], d['type'], d['from'], d['to'], d['url'],
			sCustID, sCSR
		], 2)

def process_hrt(conf, data):
	"""Process HRT

	Processes the HRT missed calls data and adds it to the HRT missed calls
	sheet

	Arguments:
		conf (dict): Key and worksheet name to write to
		data (dict[]): List of data to process

	Returns:
		None
	"""

	# Go through each item in the data
	for d in data:

		# Get the customer ID
		sCustID = get_customer(d['from'])

		# Write to the worksheet
		GSheets.insert('sg', conf['key'], conf['worksheet'], [
			d['date'], d['time'], d['type'], d['from'], d['to'], d['url'],
			sCustID
		], 2)

def run(period=None):
	"""Run

	Checks for emails from JustCall and virtualacd.biz and parses them to
	add them to the

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	# Init the Konnektive instance
	_knk.initialise()

	# Fetch the configs
	dImapConf = Conf.get(('email', 'imap'))
	dSheetsConf = Conf.get(('missed_calls', 'sheets'))

	# Connect to the IMAP server
	try:
		if dImapConf['tls']: imap_class = imaplib.IMAP4_SSL
		else: imap_class = imaplib.IMAP4
		oIMAP = imap_class(
			dImapConf['server']['host'],
			dImapConf['server']['port']
		)
	except Exception as e:
		print(str(e))
		return False

	# Authenticate
	try:
		oIMAP.login(
			dImapConf['auth']['user'],
			dImapConf['auth']['pass']
		)
	except Exception as e:
		print(str(e))
		return False

	# Select the inbox
	sStatus, lIDs = oIMAP.select('INBOX')

	# Parse the JustCall emails
	dData = justcall.parse(oIMAP)

	# Process the default calls
	process_default(dSheetsConf['default'], dData['default'])

	# Process the hrt calls
	process_hrt(dSheetsConf['hrt'], dData['hrt'])

	# Parse signia emails
	lData = signia.parse(oIMAP)

	# Process the default calls
	process_default(dSheetsConf['default'], lData)
