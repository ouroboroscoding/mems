# coding=utf8
""" Payments Service

Handles communicating with payment services
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-04-08"

# Python imports
import os, platform

# Pip imports
from RestOC import Conf, REST, Services

# App imports
from services.payments import Payments

# Load the config
Conf.load('../config.json')
sConfOverride = '../config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Create the REST config instance
oRestConf = REST.Config(Conf.get("rest"))

# Set verbose mode if requested
if 'VERBOSE' in os.environ and os.environ['VERBOSE'] == '1':
	Services.verbose()

# Get all the services
dServices = {k:None for k in Conf.get(('rest', 'services'))}
dServices['payments'] = Payments()

# Register all services
Services.register(dServices, oRestConf, Conf.get(('services', 'salt')))

# Create the HTTP server and map requests to service
REST.Server({

	# Transaction requests
	"/authorization": {"methods": REST.CREATE},
	"/capture": {"methods": REST.CREATE},
	"/credit": {"methods": REST.CREATE},
	"/refund": {"methods": REST.CREATE},
	"/sale": {"methods": REST.CREATE},
	"/validate": {"methods": REST.CREATE},
	"/void": {"methods": REST.CREATE},

	# Customer requests
	"/customer/switch": {"methods": REST.UPDATE}

}, 'payments').run(
	host=oRestConf['payments']['host'],
	port=oRestConf['payments']['port'],
	workers=oRestConf['payments']['workers']
)
