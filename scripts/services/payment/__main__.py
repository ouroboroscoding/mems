# coding=utf8
""" Payment Service

Handles interactions with Payment
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-11"

# Python imports
import os, platform

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL, REST, \
					Services, Sesh, Templates

# App imports
from services.payment import Payment

# Load the config
Conf.load('../config.json')
sConfOverride = '../config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add the global prepend and primary host to mysql
Record_Base.dbPrepend(Conf.get(("mysql", "prepend"), ''))
Record_MySQL.addHost('primary', Conf.get(("mysql", "hosts", "primary")))

# Create the REST config instance
oRestConf = REST.Config(Conf.get("rest"))

# Set verbose mode if requested
if 'VERBOSE' in os.environ and os.environ['VERBOSE'] == '1':
	Services.verbose()

# Get all the services
dServices = {"payment": Payment()}

# Register all services
Services.register(dServices, oRestConf, Conf.get(('services', 'salt')))

# Init Templates
Templates.init('../templates')

# Create the HTTP server and map requests to service
REST.Server({
	"/auth": {"methods": REST.CREATE},
	"/capture": {"methods": REST.CREATE},
	"/credit": {"methods": REST.CREATE},
	"/rebill": {"methods": REST.CREATE},
	"/sale": {"methods": REST.CREATE},
	"/void": {"methods": REST.CREATE}

}, 'payment', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['payment']['host'],
	port=oRestConf['payment']['port'],
	workers=oRestConf['payment']['workers']
)
