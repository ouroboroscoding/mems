# coding=utf8
"""Communications REST

Loads the Communications service and maps HTTP requests to specific Service
requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-03-30"

# Python imports
import os, platform

# Pip imports
from RestOC import Conf, REST, Services, SMTP

# App imports
from services.communications import Service as Communications

# Local imports
from . import serviceError

# Only run if called directly
if __name__ == "__main__":

	# Load the config
	Conf.load('config.json')
	sConfOverride = 'config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Init the SMTP module
	SMTP.init(**Conf.get(('email', 'smtp')))

	# Create the REST config instance
	oRestConf = REST.Config(Conf.get("rest"))

	# Set verbose mode if requested
	if 'VERBOSE' in os.environ and os.environ['VERBOSE'] == '1':
		Services.verbose()

	# Register the Services that will be accessible
	Services.register({
		"communications": Communications()
	}, oRestConf, Conf.get(('services', 'salt')))

	# Create the HTTP server and map requests to service
	REST.Server({
		"/email": {"methods": REST.POST},
		"/sms": {"methods": REST.POST}
		},
		'communications',
		error_callback=serviceError
	).run(
		host=oRestConf['communications']['host'],
		port=oRestConf['communications']['port'],
		workers=oRestConf['communications']['workers'],
		timeout='timeout' in oRestConf['communications'] and oRestConf['communications']['timeout'] or 30
	)
