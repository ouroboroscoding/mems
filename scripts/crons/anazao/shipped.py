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

# Shared imports
from shared import Email, Memo

# Service imports
from services.monolith.records import KtCustomer

# Cron imports
from crons import isRunning

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
		markread=False
	)

	# If we got no emails
	if not lEmails:
		return True

	# Go througg each email
	for d in lEmails:
		print(d)

	"""
		# Try to find the customer by Name and Zip
		dKtCustomer = KtCustomer.byNameAndZip(
			lMatches[3],
			lMatches[7]
		)

	# Send the tracking to Memo
	dRes = Memo.create('rest/shipping', [{
		"code": d['tracking'],
		"type": 'FDX',
		"date": d['shipped'],
		"customerId": sCrmID['customerId']
	} for d in dData])
	if dRes['error']:
		print(dRes['error'])
	"""
	# Return OK
	return True
