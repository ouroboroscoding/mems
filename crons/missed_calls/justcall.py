# coding=utf8
"""JustCall

Checks for emails from JustCall missed calls, then parses out the data and
returns it
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-10"

# Python imports
import email
import re
import traceback

# Pip imports
from RestOC import Conf

# Cron imports
from crons import emailError

reBody = re.compile(
	r"You have a new voicemail from ([a-zA-Z ']+\(\d+\) |\d+) on ([^\.]+)\.\s+" \
		"Here's the link to listen to this recording - (http:\/\/[^\s]+)",
	re.M | re.U
)
reDateHeader = re.compile(
	r'Date: [A-Z][a-z]{2}, (\d{1,2} [A-Z][a-z]{2} 20\d{2}) ' \
		'(\d{2}:\d{2}:\d{2}) \+0000',
	re.M | re.U)
"""Regex to parse data out of email"""

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

def parse(server):
	"""Parse

	Looks for unread missed call emails from JustCall and parses out the data

	Arguments:
		server (IMAP4): The server to fetch emails from

	Returns:
		list
	"""

	# Init the return list
	lRet = []

	# Fetch the config
	dConf = Conf.get(('missed_calls', 'justcall'))

	# Search for unseen emails
	sStatus, lIDs = server.search(None, '(UNSEEN FROM "%s")' % dConf['from'])

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

			# Find the date/time
			lDate = reDateHeader.search(sBody)

			# Load the email into the email library
			oMsg = email.message_from_string(sBody)

			try:

				# Find the info we need in the payload
				lPayload = oMsg.get_payload()
				lMatches = reBody.search(lPayload[0].get_payload(decode=True).decode('utf-8'))
				lMatches = lMatches.groups();

				# If there's no group
				if lMatches[1] not in dConf['numbers']:
					emailError('Unknown Missed Call Number', str(lMatches))
					continue

				# Store the data in the result var
				lRet.append({
					"date": lDate.group(1),
					"time": lDate.group(2),
					"type": 'MISSED',
					"url": lMatches[2],
					"from": extractPhone(lMatches[0])[-10:],
					"to": lMatches[1]
				})

				# Mark message as read
				server.store(sID, '+FLAGS', '\Seen')

			except Exception as e:
				# Generate the body of the email
				sBody = '%s\n\n%s\n\n%s' % (
					', '.join([str(s) for s in e.args]),
					traceback.format_exc(),
					sBody
				)
				emailError('JustCall Missed Calls Error', sBody)

	# Return anything found
	return lRet
