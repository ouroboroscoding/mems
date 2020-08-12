# coding=utf8
"""Signia

Checks for emails from Signia missed calls, then parses out the data and returns
it
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

reEmail = re.compile(
	r'Call was made on (\d{2}-\d{2}-\d{4}) at (\d{2}:\d{2}:\d{2}) with a ' \
		'call result of ([A-Z]+)\.\s*A voicemail has been left: ([^\s]+)\s*' \
		'ANI:(\d+)\s*DNIS:(\d+)',
	re.M | re.U
)
"""Regex to parse data out of email"""

def convert_date(val):
	"""Convert Date

	Takes a MM-DD-YYYY format and turns it into YYYY-MM-DD

	Args:
		val {str} -- The date to convert

	Returns:
		str
	"""

	# Split the string
	lDate = val.split('-')

	# Rebuild and return
	return '%s-%s-%s' % (
		lDate[2],
		lDate[0],
		lDate[1]
	)

def parse(server):
	"""Parse

	Looks for unread missed call emails from Signia and parses out the data

	Arguments:
		server (IMAP4): The server to fetch emails from

	Returns:
		list
	"""

	# Init the return list
	lRet = []

	# Search for unseen emails
	sStatus, lIDs = server.search(None, '(UNSEEN FROM "%s")' % Conf.get(('missed_calls', 'signia')))

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

			try:

				# Find the info we need in the payload
				lMatch = reEmail.search(oMsg.get_payload())

				# Store the data in the return var
				lRet.append({
					"date": convert_date(lMatch.group(1)),
					"time": lMatch.group(2),
					"type": lMatch.group(3),
					"url": lMatch.group(4),
					"from": lMatch.group(5),
					"to": lMatch.group(6)
				})

				# Mark message as read
				server.store(sID, '+FLAGS', '\Seen')

			except Exception as e:
				# Generate the body of the email
				sBody = '%s\n\n%s' % (
					', '.join([str(s) for s in e.args]),
					traceback.format_exc()
				)
				emailError('Missed Calls Error', sBody)

	# Return anything found
	return lRet
