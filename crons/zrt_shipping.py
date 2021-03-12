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
from records.monolith import KtCustomer, HrtPatient, ShippingInfo, SMSTemplate

# Cron imports
from . import isRunning, emailError

reUPS = re.compile(
	r'Tracking Number:\s+([A-Z0-9]+)\s+(https?:\/\/.*?datesent=([0-9]{8}).*)\s+Ship To:\s+([^\n]+)\s+([^\n]+)\s+([^,]+),\s+([A-Z]{2})\s+([0-9]{5}(?:-[0-9]{4})?)\s+US',
	re.M | re.U
)
"""UPS RegEx"""

reUSPS = re.compile(
	r'A package was shipped to you on ([0-9]{2}\/[0-9]{2}\/[0-9]{4}) via U\.S\. Postal Service Priority Mail, Small Flat Rate Box to the following address:\s+' \
	r'([^\n]+)\s+([^\n]+)\s+(.+?)\s+([A-Z]{2})\s+([0-9]{5}(?:-[0-9]{4})?)\s+' \
	r'The following optional services were used:\s+([^\n]+)\s+' \
	r'The package\'s USPS Tracking ID is ([^\n]+)\s+' \
	r'To check the delivery status of your package at any time please visit:\s+([^\n]+)',
	re.M | re.U
)
"""USPS RegEx"""

HRT_GROUP = 4
ZRT_KIT_SHIPPED = 27
ZRT_KIT_DELIVERED = 28
"""HRT/SMS ids"""

def UPS(conf):
	"""UPS

	Fetch and parse the UPS emails

	Arguments:
		conf (dict): The config data

	Returns:
		list
	"""

	# Init the return
	lRet = []

	# Try to get UPS emails
	lEmails = Email.fetch_imap(
		user=conf['auth']['user'],
		passwd=conf['auth']['pass'],
		host=conf['server']['host'],
		port=conf['server']['port'],
		tls=conf['tls'],
		from_='pkginfo@ups.com',
		markread=True
	)

	# If we got no emails
	if lEmails:

		# Go througg each email
		for d in lEmails:

			# Replace \r\n with \n
			d['text'] = d['text'].decode('utf8').replace('\r\n', '\n')

			# If status has changed
			if 'The status of your package has changed.' in d['text']:
				continue

			# Parse the text
			oMatch = reUPS.search(d['text'])

			# If we didn't find the match
			if not oMatch:
				emailError('ZRT Shipping Error', 'No regex match for:\n\n%s' % d['text']);
				continue

			# Store the matches
			lMatches = oMatch.groups();

			# Is this a delivery
			if 'your package has been delivered' in d['text']:
				iStep = ZRT_KIT_DELIVERED

			# Else if the package was shipped
			elif 'You have a package coming' in d['text']:
				iStep = ZRT_KIT_SHIPPED

			# Unknown email
			else:
				emailError('ZRT Shipping Error', 'Unknown email type:\n\n%s\n\n%s' % (
					dKtCustomer['customerId'],
					str(lMatches)
				))
				continue

			# Add the data to the list
			lRet.append({
				"name": lMatches[3],
				"zip": lMatches[7][:5],
				"code": lMatches[0],
				"company": 'UPS',
				"date": '%s-%s-%s' % (lMatches[2][4:8], lMatches[2][0:2], lMatches[2][2:4]),
				"step": iStep,
				"url": lMatches[1]
			})

	# Return what was found
	return lRet

def USPS(conf):
	"""USPS

	Fetch and parse the UPS emails

	Arguments:
		conf (dict): The config data

	Returns:
		list
	"""

	# Init the return
	lRet = []

	# Try to get UPS emails
	lEmails = Email.fetch_imap(
		user=conf['auth']['user'],
		passwd=conf['auth']['pass'],
		host=conf['server']['host'],
		port=conf['server']['port'],
		tls=conf['tls'],
		from_='no-reply@zrtlab.com',
		markread=False
	)

	# If we got no emails
	if lEmails:

		# Go througg each email
		for d in lEmails:

			# Replace \r\n with \n
			d['text'] = d['text'].decode('utf8').replace('\r\n', '\n')

			# Parse the text
			oMatch = reUSPS.search(d['text'])

			# If we didn't find the match
			if not oMatch:
				emailError('ZRT Shipping Error', 'No regex match for:\n\n%s' % d['text']);
				continue

			# Store the matches
			lMatches = oMatch.groups();

			# Add the data to the list
			lRet.append({
				"name": lMatches[1],
				"zip": lMatches[5][:5],
				"code": lMatches[7],
				"company": 'USPS',
				"date": '%s-%s-%s' % (lMatches[0][6:10], lMatches[0][0:2], lMatches[0][3:5]),
				"step": ZRT_KIT_SHIPPED,
				"url": lMatches[8]
			})

	# Return what was found
	return lRet

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

	# Get config
	dConf = Conf.get(('email', 'imap'))

	# Init the list of tracking info
	lTracking = []

	# Parse the UPS emails
#	lTracking.extend(
#		UPS(dConf)
#	)

	# Parse the USPS emails
	lTracking.extend(
		USPS(dConf)
	)

	# Go through each of the tracking we found
	for d in lTracking:

		# Try to find the customer by Name and Zip
		dKtCustomer = KtCustomer.byNameAndZip(d['name'], d['zip'])

		# If no customer
		if not dKtCustomer:
			#emailError('ZRT Shipping Error', 'No customer found for:\n\n%s' % str(d))
			continue

		# Look for an HRT Patient record that's still onboarding
		oHrtPatient = HrtPatient.filter({
			"ktCustomerId": dKtCustomer['customerId'],
			"stage": 'Onboarding',
			"processStatus": 'Ordered Lab Kit'
		}, limit=1)

		# If there's an HRT patient
		if oHrtPatient:

			# If the kit was shipped
			if d['step'] == ZRT_KIT_SHIPPED:
				oHrtPatient['processStatus'] = 'Shipped Lab Kit';

			# Else if it was delivered
			elif d['step'] == ZRT_KIT_DELIVERED:
				oHrtPatient['processStatus'] = 'Delivered Lab Kit'

			# Save the record
			oHrtPatient.save()

		# If it's shipped
		if d['step'] == ZRT_KIT_SHIPPED:

			# Get current date/time
			sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

			# Create an instance of the shipping record
			try:
				oShipInfo = ShippingInfo({
					"customerId": dKtCustomer['customerId'],
					"code": d['code'],
					"type": d['company'],
					"date": d['date'],
					"createdAt": sDT,
					"updatedAt": sDT
				})
			except ValueError as e:
				emailError('ZRT Shipping Error', 'Couldn\'t create ShippingInfo for:\n\n%s\n\n%s\n\n%s' % (
					dKtCustomer['customerId'],
					str(d),
					str(e.args)
				))
				continue

			# Create the record
			oShipInfo.create(conflict='replace');

			# If it's with UPS
			if d['company'] == 'UPS':

				# Send kit shipped email
				dTpl = {
					"name": "%s %s" % (
						dKtCustomer['firstName'],
						dKtCustomer['lastName']
					),
					"link": d['url']
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
						str(d),
						str(oResponse)
					))

		# If it's with UPS
		if d['company'] == 'UPS':

			# Find the template
			dSmsTpl = SMSTemplate.filter({
				"groupId": HRT_GROUP,
				"type": 'sms',
				"step": d['step']
			}, raw=['content'], limit=1)

			# Convert any arguments
			sContent = dSmsTpl['content']. \
					replace('{tracking_code}', d['code']). \
					replace('{tracking_date}', d['date']) . \
					replace('{tracking_link}', d['url']). \
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
					str(oResponse),
					str(dKtCustomer),
					str(d)
				))

	# Return OK
	return True
