# coding=utf8
""" Memo Service

Handles everything in the old memo system
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-04-26"

# Python imports
import os, platform

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL, REST, \
					Services, Sesh, Templates

# App imports
from services.memo import Memo

# Load the config
Conf.load('../config.json')
sConfOverride = '../config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add the global prepend and primary host to mysql
Record_Base.dbPrepend(Conf.get(("mysql", "prepend"), ''))
Record_MySQL.addHost('memo', Conf.get(("mysql", "hosts", "memo")))

# Init the Sesh module
Sesh.init(Conf.get(("redis", "primary")))

# Create the REST config instance
oRestConf = REST.Config(Conf.get("rest"))

# Set verbose mode if requested
if 'VERBOSE' in os.environ and os.environ['VERBOSE'] == '1':
	Services.verbose()

# Get all the services
dServices = {k:None for k in Conf.get(('rest', 'services'))}
dServices['memo'] = Memo()

# Register all services
Services.register(dServices, oRestConf, Conf.get(('services', 'salt')))

# Init Templates
Templates.init('../templates')

# Create the HTTP server and map requests to service
REST.Server({
	"/passwd/forgot": {"methods": REST.CREATE | REST.UPDATE},

	"/session": {"methods": REST.READ, "session": True},

	"/signin": {"methods": REST.POST},
	"/signout": {"methods": REST.POST, "session": True},

	"/user": {"methods": REST.READ | REST.UPDATE, "session": True},
	"/user/passwd": {"methods": REST.UPDATE, "session": True},

	"/msgs/claimed": {"methods": REST.READ, "session": True},
	"/msgs/unclaimed": {"methods": REST.READ, "session": True}

}, 'memo', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['memo']['host'],
	port=oRestConf['memo']['port'],
	workers=oRestConf['memo']['workers']
)
