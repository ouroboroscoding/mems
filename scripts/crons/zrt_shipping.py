# coding=utf8
"""ZRT Shipping

Parses emails from UPS for ZRT shipping and adds them to the DB
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-07-28"

# Python imports
import re

# Pip imports
import arrow
from RestOC import Conf, Record_MySQL, Services, Sesh

# Shared imports
from shared import Email

# Service imports
from services.monolith.records import KtCustomer, ShippingInfo

# Cron imports
from . import isRunning

reContent = re.compile(
	r'Tracking Number:\s+([A-Z0-9]+)\s+http:\/\/.*?datesent=([0-9]{8})\s+Ship To:\s+([^\n]+)\s+([^\n]+)\s+([^,]+),\s+([A-Z]{2})\s+([0-9]{5}(?:-[0-9]{4})?)\s+US',
	re.M | re.U
)

def emailError(error):
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
		"subject": 'ZRT Shipping Error',
		"to": Conf.get(('developer', 'emails'))
	})
	if oEff.errorExists():
		print(oEff.error)
		return False

	# Return OK
	return True

def run():
	"""Run

	Entry point into the script

	Arguments:
		type (str): The type of report to generate
		arg1 (str): Possible data passed to the report

	Returns:
		int
	"""

	# If the script already running?
	if isRunning('zrt_shipping'):
		return True

	# Try to get UPS emails
	lEmails = Email.fetch_imap(
		user='sg@maleexcel.com',
		passwd='Revita123!',
		host='maleexcel.com',
		port=993,
		tls=True,
		from_='pkginfo@ups.com',
		markread=False
	)

	# If we got no emails
	if not lEmails:
		return 1

	# Go througg each email
	for d in lEmails:

		# Replace \r\n with \n
		d['text'] = d['text'].decode('utf8').replace('\r\n', '\n')

		# Parse the text
		oMatch = reContent.search(d['text'])

		# If we didn't find the match
		if not oMatch:
			emailError('No regex match for:\n\n%s' % d['text']);
			continue

		# Store the matches
		lMatches = oMatch.groups();
		print(str(lMatches));

		# Try to find the customer by Name and Zip
		dKtCustomer = KtCustomer.byNameAndZip(
			lMatches[2],
			lMatches[6]
		)

		# If no customer
		if not dKtCustomer:
			emailError('No customer found for:\n\n%s' % str(lMatches))
			continue

		# Get current date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Create an instance of the shipping record
		try:
			oShipInfo = ShippingInfo({
				"customerId": dKtCustomer['customerId'],
				"code": lMatches[0],
				"type": 'UPS',
				"date": '%s-%s-%s' % (lMatches[1][4:8], lMatches[1][0:2], lMatches[1][2:4]),
				"createdAt": sDT,
				"updatedAt": sDT
			})
		except ValueError as e:
			emailError('Couldn\'t create ShippingInfo for :\n\n%s\n\n%s' % (
				dKtCustomer['customerId'],
				str(lMatches.groups())
			))
			continue

		# Create the record
		oShipInfo.create(conflict='replace');


	# Return OK
	return 1
