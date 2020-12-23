# coding=utf8
"""Contact Form

Checks SG mail about contact form messages
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-12-23"

# Python imports
import imaplib
import traceback

# Pip imports
from RestOC import Conf, Services

# Records
from records.monolith import KtCustomer

def extractPhone(val):
	"""Extract Phone Number

	Takes a string and extracts the digits of the phone number

	Args:
		val {str} -- String to extract

	Returns:
		str
	"""

	phoneNumber = ""

	for character in val:
		if character.isdigit():
			phoneNumber = phoneNumber + character

	return phoneNumber

def parse_emails(server):
	"""Parse Emails

	Gets the unread e-mails from a specific address, parses
	out the relevant data, and returns the list

	Arguments:
		server (IMAP4): The server to fetch emails from

	Returns:
		list
	"""

	# Search for unseen emails
	sStatus, lIDs = server.search(None, '(UNSEEN FROM "%s")' % Conf.get(('contact_form', 'from')))

	# If there are IDs
	if(lIDs[0]):

		# Split them
		lIDs = lIDs[0].split(b' ')

		# Step through them
		for sID in lIDs:

			# Fetch the email
			sTyp, lData = server.fetch(sID, '(BODY.PEEK[])')

			# Get the raw data
			sBody = lData[0][1].decode('utf-8')

			# Load the email into the email library
			oMsg = email.message_from_string(sBody)

			# Find the info we need in the payload
			lMatch = reEmail.search(oMsg.get_payload())

			# Store the data in the result var
			lRet.append({
				"date": lMatch.group(1),					# Date
				"time": lMatch.group(2),					# Time
				"name": lMatch.group(3),					# Name
				"email": lMatch.group(4),					# Email
				"phone": extractPhone(lMatch.group(5)),		# Phone
				"content": lMatch.group(6)					# Content
			})

			# Mark message as read
			server.store(sID, '+FLAGS', '\Seen')

	# Return the found data
	return lRet

def process(emails):
	"""Process

	Adds the form data as a fake SMS message for use by the agents

	Arguments:
		data (dict[]): List of data to process

	Returns:
		None
	"""
"""
	# Go through each missed call
	for d in data:

		# If there's no content
		if not d['content']:
			continue

		# If the content has any BRs
		if '<br />' in d['content'] or
			'<br/>' in d['content'] or
			'<br>' in d['content']

		# If there's no phone number
		if not d['phone']:

			# Try to find the customer by email
			dCustomer = KtCustomer.filter({
				"emailAddress": d['email']
			}, raw=['phoneNumber'], limit=1, orderby=[['updatedAt', 'DESC']])

			# If we got one
			if dCustomer:
				d['phone'] = dCustomer['phoneNumber']

			# Email Eddy
			else:
				Services.create('communications', 'email', {

				})

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
"""

def run():
	"""Run

	Main entry point

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

		# Get and parse the emails
		lData = parse_emails(oIMAP)

		# If there's emails
		if lData:

			# Process the emails
			process(lData)

	# Catch any error and email it
	except Exception as e:
		sBody = '%s\n\n%s' % (
			', '.join([str(s) for s in e.args]),
			traceback.format_exc()
		)
		emailError('Missed Calls Failed', sBody)
		return False
