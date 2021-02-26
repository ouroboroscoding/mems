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
import imaplib
import traceback

# Pip imports
from RestOC import Conf, Services

# Service imports
from services.konnektive import Konnektive

# Cron imports
from crons import emailError, isRunning

# Local imports
from . import signia

def process(data):
	"""Process

	Adds the missed call as a fake SMS message for use by the agents

	Arguments:
		data (dict[]): List of data to process

	Returns:
		None
	"""

	# Go through each missed call
	for d in data:

		# Add the request as an incoming SMS
		oResponse = Services.create('monolith', 'message/incoming', {
			"_internal_": Services.internalKey(),
			"customerPhone": d['from'],
			"recvPhone": "0000000000",
			"content": "MISSED CALL:\nSent to %s at %s %s\n[url=Click to listen|%s]" % (
				d['to'],
				d['date'],
				d['time'],
				d['url']
			)
		})
		if oResponse.errorExists():
			emailError('Missed Call Request Failed', 'Failed to add SMS\n\n%s\n\n%s' % (
				str(d),
				str(oResponse)
			))

def run(period=None):
	"""Run

	Checks for emails from JustCall and virtualacd.biz and parses them to
	add them to the

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	try:

		# Fetch the configs
		dImapConf = Conf.get(('email', 'imap'))

		# Connect to the IMAP server
		if dImapConf['tls']: imap_class = imaplib.IMAP4_SSL
		else: imap_class = imaplib.IMAP4
		oIMAP = imap_class(
			dImapConf['server']['host'],
			dImapConf['server']['port']
		)

		# Authenticate
		oIMAP.login(
			dImapConf['auth']['user'],
			dImapConf['auth']['pass']
		)

		# Select the inbox
		sStatus, lIDs = oIMAP.select('INBOX')

		# Parse signia emails
		lData = signia.parse(oIMAP)

		# Process the default calls
		process(lData)

		# Return OK
		return True

	# Catch any error and email it
	except Exception as e:
		sBody = '%s\n\n%s' % (
			', '.join([str(s) for s in e.args]),
			traceback.format_exc()
		)
		emailError('Missed Calls Failed', sBody)
		return False
