# coding=utf8
""" External Node

Handles logins and letting them sign in/out
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
from RestOC import Conf, REST, Services

# Local imports
from . import reqJSON, resJSON

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

def emailError(subject, error):
	"""Email Error

	Send out an email with an error message

	Arguments:
		error (str): The error to email

	Returns:
		bool
	"""

	# For debugging
	print('Emailing: %s, %s' % (subject, error))

	# Send the email
	oResponse = Services.create('communications', 'email', {
		"_internal_": Services.internalKey(),
		"text_body": error,
		"subject": subject,
		"to": Conf.get(('developer', 'emails'))
	})
	if oResponse.errorExists():
		print(oResponse.error)
		return False

	# Return OK
	return True


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

@bottle.post('/contactForm')
def contactForm():
	"""Contact Form

	Recieves data from MaleExcel.com contact form

	Returns:
		str
	"""

	# Get the body
	dData = reqJSON()

	print('----------------------------------------')
	print('ME Contact Form')
	pprint.pprint({k:bottle.request.forms.get(k) for k in bottle.request.forms.keys()})

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

	print('----------------------------------------')
	print('JustCall Webhook')
	pprint.pprint(dData)

	# Return OK
	return resJSON(True)

def show500():
	"""Show 500

	Display HTTP Status 500 error

	Returns:
		str
	"""
	bottle.response.status = 500
	return """
<!DOCTYPE html>
<html>
 <head>
  <title>500 Internal Server Error</title>
 </head>
 <body>
  <h1>500 Internal Server Error</h1>
  <p>An internal error has occured which caused your request to fail. An administrator has been notified of the failure and it will be worked on ASAP.</p>
 </body>
</html>"""

# Run the webserver
bottle.run(
	host=oRestConf['external']['host'],
	port=oRestConf['external']['port'],
	server="gunicorn",
	workers=oRestConf['external']['workers']
)
