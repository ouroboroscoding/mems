# coding=utf8
""" Link Node

Handles shortened links
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-03-08"

# Python imports
import os, platform, pprint

# Pip imports
import bottle
from RestOC import Conf, REST, Services, StrHelper

# Shared imports
from shared import Environment

# Local imports
from nodes import emailError, resJSON, show500

@bottle.get('/<code>')
def redirect(code):
	"""Redirect

	Redirects towards the url found with the code

	Returns:
		None
	"""

	# Look for the code in the service and track the request
	oResponse = Services.create('link', 'view', {
		"_internal_": Services.internalKey(),
		"code": code,
		"ip": Environment.getClientIP(bottle.request.environ),
		"agent": bottle.request.environ['HTTP_USER_AGENT']
	})

	# If we got an error
	if oResponse.errorExists():

		# If it's anything other than 1104 (Key doesn't exist)
		if oResponse.error['code'] != 1104:

			# Notify a developer of the error
			emailError(
				'Link Key Error',
				'Error: %s\n\nSent: %s' % (
					str(oResponse.error),
					str(dData)
				)
			)

			# Return an error
			return show500()

		# Code doesn't exist
		return 'Invalid code.'

	# Redirect to the URL
	return bottle.redirect(oResponse.data);

#@bottle.get('/<code>/stats')
#def stats(code):
#	"""Stats
#
#	Returns the stats on the link
#
#	Returns:
#		None
#	"""
#
#	# Look for the code in the service and track the request
#	oResponse = Services.read('link', 'stats', {
#		"_internal_": Services.internalKey(),
#		"code": code
#	})
#
#	# If we got an error
#	if oResponse.errorExists():
#
#		# If it's anything other than 1104 (Key doesn't exist)
#		if oResponse.error['code'] != 1104:
#
#			# Notify a developer of the error
#			emailError(
#				'Link Key Error',
#				'Error: %s\n\nSent: %s' % (
#					str(oResponse.error),
#					str(dData)
#				)
#			)
#
#			# Return an error
#			return show500()
#
#		# Code doesn't exist
#		return 'Invalid code'
#
#	# Return the stats
#	return resJSON(oResponse.data)

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
		host=oRestConf['link_domain']['host'],
		port=oRestConf['link_domain']['port'],
		server="gunicorn",
		workers=oRestConf['link_domain']['workers']
	)
