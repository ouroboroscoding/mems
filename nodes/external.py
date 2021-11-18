# coding=utf8
""" External Node

Handles requests by third parties who can't or won't login to the system
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-12-05"

# Python imports
import os, platform, pprint

# Pip imports
import bottle
import requests
from RestOC import Conf, REST, Services, StrHelper

# Shared imports
from shared import GSheets

# Local imports
from nodes import emailError, reqJSON, resJSON, show500

@bottle.post('/calendly/created')
def calendlyCreate():
	"""Calendly Create

	Webhook called by Calendly to notify of new created events

	Returns:
		str
	"""

	# Get the body
	dData = reqJSON()

	# If the utm source is set
	if dData['payload']['tracking']['utm_source']:

		# Notify the providers service that the key was used
		oResponse = Services.delete('providers', 'calendly/single', {
			"_internal_": Services.internalKey(),
			"_key": dData['payload']['tracking']['utm_source']
		})

		# If we got an error
		if oResponse.errorExists():

			# If it's anything other than 1104 (Key doesn't exist)
			if oResponse.error['code'] != 1104:

				# Notify a developer of the error
				emailError(
					'Calendly Create Failed',
					'Error: %s\n\nSent: %s' % (
						str(oResponse.error),
						str(dData)
					)
				)

	# Return OK
	return  resJSON(True)

@bottle.post('/calendly/canceled')
def calendlyCancelled():
	"""Calendly Cancelled

	Webhook called by Calendly to notify of new "canceled" events

	Returns:
		str
	"""

	# Get the body
	#dData = reqJSON()

	# Return OK
	return resJSON(True)

def customerIds(phone, email):
	"""Customer IDs

	Returns the list of customer IDs associated with either the phone or
	email address listed

	Arguments:
		phone (str): The phone number to look up
		email (str): The email to lookup

	Returns:
		list
	"""

	# Return list
	lRet = []

	# Get the KNK config
	dConf = Conf.get(('konnektive'))

	# Init params
	dParams = {
		"loginId": dConf['user'],
		"password": dConf['pass'],
		"startDate": '01/01/2000',
		"endDate": '01/01/3000'
	}

	# Add either the phone or email
	if phone:
		dParams['phoneNumber'] = phone
	else:
		dParams['emailAddress'] = email

	# Look up the customer
	oRes = requests.post(
		'https://%s/customer/query/' % dConf['host'],
		params=dParams
	)

	# If the result is ok
	if oRes and oRes.status_code == 200:
		dRes = oRes.json()
		if dRes['result'] == 'SUCCESS':
			for o in dRes['message']['data']:
				lRet.append('https://crm.konnektive.com/customer/cs/details/?customerId=%d' % o['customerId'])

@bottle.post('/contactForm')
def contactForm():
	"""Contact Form

	Recieves data from MaleExcel.com contact form

	Returns:
		str
	"""

	print('----------------------------------------')
	print('ME Contact Form')
	pprint.pprint({k:bottle.request.forms.get(k) for k in bottle.request.forms.keys()})

	# Get the config data
	dConf = Conf.get(('contact_form'))

	# Insert the data at the top of the gdrive sheet
	GSheets.insert(
		'sg',
		dConf['key'],
		dConf['worksheet'],
		[
			bottle.request.forms.get('date'),
			bottle.request.forms.get('time'),
			bottle.request.forms.get('name'),
			bottle.request.forms.get('email'),
			bottle.request.forms.get('phone'),
			bottle.request.forms.get('message'),
			customerIds(
				StrHelper.digits(bottle.request.forms.get('phone'))[-10:],
				bottle.request.forms.get('email')
			)
		],
		2
	)

	# Return OK
	return resJSON(True)

@bottle.post('/justcall')
def justCallWebhook():
	"""JustCall Webhook

	Webhook called by JustCall when new calls occur

	Returns:
		str
	"""

	# Get the body
	dData = reqJSON()
	dData = dData['data']

	# If there's no type, but there is a signature, just return OK
	if 'type' not in dData and 'signature' in dData:
		return resJSON(True)

	pprint.pprint(dData)

	# If the type is a call
	if dData['type'] == 'call':

		# If the subject starts with 'Voicemail from ''
		if dData['subject'][0:15] == 'Voicemail from ':

			# Generate incoming content
			sContent = "VOICEMAIL:\nSent to %s (%s)\n%s%s" % (
				dData['agent_name'],
				dData['called_via'][-10:],
				dData['ivr'] and ('(%s) %s\n' % (dData['ivr']['digit'], dData['ivr']['digit_description'])) or '',
				dData['recording_url'] and \
					('[url=Click to listen|%s]' % dData['recording_url']) or \
					'no recording found'
			)

			# Add the request as an incoming SMS
			oResponse = Services.create('monolith', 'message/incoming', {
				"_internal_": Services.internalKey(),
				"customerPhone": dData['contact_number'][-10:],
				"recvPhone": "0000000000",
				"content": sContent
			})
			if oResponse.errorExists():
				emailError('JustCall Webhook Request Failed', 'Failed to add SMS\n\n%s\n\n%s' % (
					str(dData),
					str(oResponse)
				))

			# Generate outgoing content
			sContent = "MALE EXCEL MEDICAL: We have missed a call from your number. " \
						"All our agents are currently assisting other patients. The " \
						"next available agent will contact you in the shortest " \
						"possible delay. Please note that all calls outside of " \
						"office hours  will be returned upon reopening.\n\n" \
						"If you would prefer that we contact you via text please " \
						"reply \"Text\" otherwise our agents will reach out by phone."

			# Send the message to the customer
			oResponse = Services.create('monolith', 'message/outgoing', {
				"_internal_": Services.internalKey(),
				"store_on_error": True,
				"auto_response": True,
				"customerPhone": dData['contact_number'][-10:],
				"content": sContent,
				"name": "SMS Workflow",
				"type": "support"
			})
			if oResponse.errorExists():
				emailError('JustCall Webhook Request Failed', 'Failed to send Auto-Response SMS\n\n%s\n\n%s' % (
					str(dData),
					str(oResponse)
				))

	# Else, if it's an incoming queue enter
	elif dData['type'] == 'call_queue_enter':

		# Store the call
		oResponse = Services.create('justcall', 'queue', {
			"_internal_": Services.internalKey(),
			"call_sid": dData['call_sid'],
			"datetime": dData['datetime'],
			"contact_number": dData['contact_number'],
			"justcall_number": dData['justcall_number'],
			"ivr": '(%s) %s' % (
				'ivr_digit' in dData and dData['ivr_digit'] or '?',
				'ivr_digit_description' in dData and dData['ivr_digit_description'] or '',
			)
		})

		# If there was an error
		if oResponse.errorExists():
			emailError('JustCall Webhook call_queue_enter Error', 'Failed to add call\n\n%s\n\n%s' % (
				str(dData),
				str(oResponse)
			))

	# Else, if it's an incoming queue exit
	elif dData['type'] == 'call_queue_exit':

		# Figure out the reason
		if dData['reason']['code'] == '0' and 'voicemail' in dData['reason']['code_description']:
			sReason = '2'
		else:
			sReason = dData['reason']['code']

		# Delete the call
		oResponse = Services.delete('justcall', 'queue', {
			"_internal_": Services.internalKey(),
			"call_sid": dData['call_sid'],
			"reason": sReason
		})

		# If there was an error
		if oResponse.errorExists():
			emailError('JustCall Webhook call_queue_exit Error', 'Failed to remove call\n\n%s\n\n%s' % (
				str(dData),
				str(oResponse)
			))

	# Return OK
	return resJSON(True)

# Only run if called directly
if __name__ == "__main__":

	# Load the config
	Conf.load('config.json')
	sConfOverride = 'config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Create the REST config instance
	oRestConf = REST.Config(Conf.get("rest"))

	# Get all the services
	dServices = {k:None for k in Conf.get(('rest', 'services'))}

	# Register all services
	Services.register(dServices, oRestConf, Conf.get(('services', 'salt')))

	# Run the webserver
	bottle.run(
		host=oRestConf['external']['host'],
		port=oRestConf['external']['port'],
		server="gunicorn",
		workers=oRestConf['external']['workers']
	)
