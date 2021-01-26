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
from RestOC import Conf, Record_MySQL, Services, Sesh, Templates

# Shared imports
from shared import Email

# Service imports
from records.monolith import KtCustomer, ShippingInfo, SMSTemplate

# Cron imports
from . import isRunning, emailError

reContent = re.compile(
	r'Tracking Number:\s+([A-Z0-9]+)\s+(https?:\/\/.*?datesent=([0-9]{8}).*)\s+Ship To:\s+([^\n]+)\s+([^\n]+)\s+([^,]+),\s+([A-Z]{2})\s+([0-9]{5}(?:-[0-9]{4})?)\s+US',
	re.M | re.U
)

HRT_GROUP = 4
ZRT_KIT_SHIPPED = 27
ZRT_KIT_DELIVERED = 28

def run():
	"""Run

	Entry point into the script

	Arguments:
		type (str): The type of report to generate
		arg1 (str): Possible data passed to the report

	Returns:
		bool
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
		markread=True
	)

	# If we got no emails
	if not lEmails:
		return True

	# Go througg each email
	for d in lEmails:

		# Replace \r\n with \n
		d['text'] = d['text'].decode('utf8').replace('\r\n', '\n')

		# If status has changed
		if 'The status of your package has changed.' in d['text']:
			continue

		# Parse the text
		oMatch = reContent.search(d['text'])

		# If we didn't find the match
		if not oMatch:
			emailError('ZRT Shipping Error', 'No regex match for:\n\n%s' % d['text']);
			continue

		# Store the matches
		lMatches = oMatch.groups();

		# Try to find the customer by Name and Zip
		dKtCustomer = KtCustomer.byNameAndZip(
			lMatches[3],
			lMatches[7]
		)

		# If no customer
		if not dKtCustomer:
			emailError('ZRT Shipping Error', 'No customer found for:\n\n%s' % str(lMatches))
			continue

		# Make the date readable
		sDate = '%s-%s-%s' % (lMatches[2][4:8], lMatches[2][0:2], lMatches[2][2:4])

		# Is this a delivery
		if 'your package has been delivered' in d['text']:

			# Step
			iStep = ZRT_KIT_DELIVERED

		# Else if the package was shipped
		elif 'You have a package coming' in d['text']:

			# Get current date/time
			sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

			# Create an instance of the shipping record
			try:
				oShipInfo = ShippingInfo({
					"customerId": dKtCustomer['customerId'],
					"code": lMatches[0],
					"type": 'UPS',
					"date": sDate,
					"createdAt": sDT,
					"updatedAt": sDT
				})
			except ValueError as e:
				emailError('ZRT Shipping Error', 'Couldn\'t create ShippingInfo for:\n\n%s\n\n%s' % (
					dKtCustomer['customerId'],
					str(lMatches)
				))
				continue

			# Create the record
			oShipInfo.create(conflict='replace');

			# Step
			iStep = ZRT_KIT_SHIPPED

			# Send kit shipped email
			dTpl = {
				"name": "%s %s" % (
					dKtCustomer['firstName'],
					dKtCustomer['lastName']
				),
				"link": lMatches[1]
			}

			# Send the Email to the patient
			oResponse = Services.create('communications', 'email', {
				"_internal_": Services.internalKey(),
				"from": 'noreply@m.maleexcelmail.com',
				"html_body": Templates.generate('email/crons/zrt_test_kit_shipped.html', dTpl, 'en-US'),
				"subject": Templates.generate('email/crons/zrt_test_kit_shipped.txt', {}, 'en-US'),
				"to": dKtCustomer['emailAddress']
			})
			if oResponse.errorExists():
				emailError('ZRT Shipping Error', 'Couldn\'t send email:\n\n%s\n\n%s\n\n%s' % (
					str(dKtCustomer),
					str(lMatches),
					str(oResponse)
				))

		# Unknown email
		else:
			emailError('ZRT Shipping Error', 'Unknown email type:\n\n%s\n\n%s' % (
				dKtCustomer['customerId'],
				str(lMatches)
			))

		# Find the template
		dSmsTpl = SMSTemplate.filter({
			"groupId": HRT_GROUP,
			"type": 'sms',
			"step": iStep
		}, raw=['content'], limit=1)

		# Convert any arguments
		sContent = dSmsTpl['content']. \
				replace('{tracking_code}', lMatches[0]). \
				replace('{tracking_date}', sDate) . \
				replace('{tracking_link}', lMatches[1]). \
				replace('{patient_first}', dKtCustomer['firstName']). \
				replace('{patient_last}', dKtCustomer['lastName']). \
				replace('{patient_name}', '%s %s' % (dKtCustomer['firstName'], dKtCustomer['lastName']))

		# Send the SMS to the patient
		oResponse = Services.create('monolith', 'message/outgoing', {
			"_internal_": Services.internalKey(),
			"name": "HRT Workflow",
			"customerPhone": dKtCustomer['phoneNumber'],
			"content": sContent,
			"type": 'support'
		})
		if oResponse.errorExists():
			emailError('ZRT Shipping Error', 'Couldn\'t send sms:\n\n%s\n\n%s\n\n%s' % (
				str(dKtCustomer),
				str(lMatches),
				str(oResponse)
			))

		# Send the Email to the patient
		"""
		oResponse = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": 'body'
			"subject": 'subject',
			"to": dKtCustomer['emailAddress']
		})
		if oResponse.errorExists():
			emailError('ZRT Shipping Error', 'Couldn\'t send email:\n\n%s\n\n%s\n\n%s' % (
				dKtCustomer['customerId'],
				str(lMatches),
				str(oResponse)
			))
		"""

	# Return OK
	return True
