# coding=utf8
"""Anazao Shipped

Parses emails from Anazao looking for shipped ones and sends the data to memo
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-10"

# Python imports
import re
import traceback

# Shared imports
from shared import Email, Memo

# Service imports
from services.monolith.records import KtCustomer

# Cron imports
from crons import isRunning, emailError

reEmail = re.compile(r'(\d{2}\/\d{2}\/\d{2}) for the patients listed below:(?:<br>){4}([^<]+)(?:<br>){4}The order is being shipped to the following address:(?:<br>){3}([^<]+)(?:<br>){4}The tracking number for this shipment is <a href="[^"]+">([^<]+)<\/a>')

# ([^,]+), ([^,]+), ([A-Z]{2}) (\d{5}) US  ([^<]+)

def convert_date(s):
	"""Convert Date

	Turn the date in the email into a valid YYYY-MM-DD format

	Arguments:
		s (str): MM/DD/YY date string

	Returns:
		str
	"""

	# Split the date by forward slash
	lDate = s.split('/')

	# Recombine and add the 20
	return '20%s-%s-%s' % (
		lDate[2], lDate[0], lDate[1]
	)

def run():
	"""Run

	Parses emails looking for shipment codes/dates

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('anazao_shipped'):
		return True

	# Try to get UPS emails
	lEmails = Email.fetch_imap(
		user='sg@maleexcel.com',
		passwd='Revita123!',
		host='maleexcel.com',
		port=993,
		tls=True,
		from_='myAnazao@AnazaoHealth.com',
		markread=True
	)

	# If we got no emails
	if not lEmails:
		return True

	# Init the list to send to Memo
	lCodes = []

	# Go througg each email
	for d in lEmails:

		# If it's not a shipped email
		if 'Have Shipped' not in d['headers']['Subject']:
			continue

		try:

			# Parse the email
			oMatch = reEmail.search(d['html'].decode('utf-8'))
			lMatches = oMatch.groups()

			# Split the address into parts
			lAddress = lMatches[2].split(', ')
			sZip = lAddress[len(lAddress) == 3 and 2 or 3].split(' ')[1]

			# Try to find the customer by Name and Zip
			dKtCustomer = KtCustomer.byNameAndZip(
				lMatches[1],
				sZip
			)

			# If no customer
			if not dKtCustomer:
				emailError('Anazao Shipping Error', 'No customer found for:\n\n%s' % str(lMatches))
				continue

			# Add it to the list
			lCodes.append({
				"code": lMatches[3],
				"type": 'FDX',
				"date": convert_date(lMatches[0]),
				"customerId": dKtCustomer['customerId']
			})

		except Exception as e:
			# Generate the body of the email
			sBody = '%s\n\n%s\n\n%s' % (
				', '.join([str(s) for s in e.args]),
				traceback.format_exc(),
				d['html']
			)
			emailError('Anazao Email Error', sBody)
			continue

	# If we got any valid emails
	if lCodes:

		# Send the tracking to Memo
		dRes = Memo.create('rest/shipping', lCodes)
		if dRes['error']:
			print(dRes['error'])
			return False

	# Return OK
	return True
