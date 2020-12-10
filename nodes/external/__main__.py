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

@bottle.post('/calendly/created')
def calendlyCreate():
	"""Calendly Create

	Webhook called by Calendly to notify of new created events

	Returns:
		str
	"""

	# Get the body
	dData = reqJSON()

	print('----------------------------------------\nNew Calendly created:')
	pprint.pprint(dData)

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
	dData = reqJSON()

	print('----------------------------------------\nNew Calendly canceled:')
	pprint.pprint(dData)

	# Return OK
	return  resJSON(True)

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
