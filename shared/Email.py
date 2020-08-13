# coding=utf8
""" Email

Shared functionality to deal with fetching / writing emails
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-07-28"

# Python imports
import base64
import email
import imaplib

def fetch_imap(user, passwd, host='localhost', port=143, tls=False, box='INBOX', from_=None, markread=True):
	"""Fetch IMAP

	Returns a list unread messages from a specific mailbox, optionally
	filtered by from address. By default this function will mark any messages
	fetched as read unless markread=False

	Arguments:
		user (str): The user of the account
		passwd (str): The password associated with the user
		host (str): The hostname of the imap server
		port (uint): The port of the imap server
		tls: (bool): True for TLS encryption
		box (str): The mailbox to fetch from
		from_ (str): Optional email address to filter messages from
		markread (bool): Sets the messages as read after fetching them

	Returns:
		list
	"""

	# Init the return list
	lRet = []

	# Connect to the IMAP server
	imap_class = tls and imaplib.IMAP4_SSL or imaplib.IMAP4
	oServer = imap_class(host, port)

	# Login
	oServer.login(user, passwd)

	# Select the mailbox
	sStatus, lIDs = oServer.select(box)

	# Set unseen flag
	sUnseen = from_ and ('(UNSEEN FROM "%s")' % from_) or '(UNSEEN)'

	# Search for unseen emails
	sStatus, lIDs = oServer.search(None, sUnseen)

	# If there are IDs
	if(lIDs[0]):

		# Split them
		lIDs = lIDs[0].split(b' ')

		# Step through them
		for sID in lIDs:

			# Init the email dict
			dEmail = {
				'attachments': None,
				'headers': {},
				'html': None,
				'text': None
			}

			# Fetch the email
			sTyp, lData = oServer.fetch(sID, '(BODY.PEEK[])')

			# Get the raw data
			sBody = lData[0][1].decode('utf-8')

			# Load the email into the email library
			oMsg = email.message_from_string(sBody)

			# Get the headers
			for l in oMsg.items():
				dEmail['headers'][l[0]] = l[1]

			# If it's multipart
			if oMsg.is_multipart():

				# Get the payloads
				lPayloads = oMsg.get_payload()

				# Go through each one and print what it is
				for o in lPayloads:

					# If the type is text/plain
					if o.get_content_type() == 'text/plain':
						dEmail['text'] = o.get_payload(decode=True)

					# Else if the type is text/html
					elif o.get_content_type() == 'text/html':
						dEmail['html'] = o.get_payload(decode=True)

					# Else it's most likely an attachment
					else:

						# If we don't have a list yet
						if dEmail['attachments'] is None:
							dEmail['attachments'] = []

						# Store the type, filename, and content
						dEmail['attachments'].append({
							"type": o.get_content_type(),
							"filename": o.get_filename(),
							"content": o.get_payload(decode=True)
						})

			# Else, it's a single part
			else:

				# Get the payload
				sPayload = oMsg.get_payload()

				# If there's encoding
				if 'Content-Transfer-Encoding' in dEmail['headers']:
					if dEmail['headers']['Content-Transfer-Encoding'] == 'base64':
						sPayload = base64.b64decode(sPayload)
					else:
						raise ValueError('Unknown Content-Transfer-Encoding: %s' % dEmail['headers']['Content-Transfer-Encoding'])

				# If it's html
				if oMsg.get_content_type() == 'text/html':
					dEmail['html'] = sPayload
				elif oMsg.get_content_type() == 'text/plain':
					dEmail['text'] = sPayload
				else:
					raise ValueError('Unknown Content-Type: %s' % oMsg.get_content_type())

			# Add the email to the return list
			lRet.append(dEmail)

			# Mark message as read
			if markread:
				oServer.store(sID, '+FLAGS', '\Seen')

	# Return any emails found
	return lRet
