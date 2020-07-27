# coding=utf8
""" Monolith Service

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
from services.monolith import Monolith

# Load the config
Conf.load('../config.json')
sConfOverride = '../config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add the global prepend and primary host to mysql
Record_Base.dbPrepend(Conf.get(("mysql", "prepend"), ''))
Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))

# Init the Sesh module
Sesh.init(Conf.get(("redis", "primary")))

# Create the REST config instance
oRestConf = REST.Config(Conf.get("rest"))

# Set verbose mode if requested
if 'VERBOSE' in os.environ and os.environ['VERBOSE'] == '1':
	Services.verbose()

# Get all the services
dServices = {k:None for k in Conf.get(('rest', 'services'))}
dServices['monolith'] = Monolith()

# Register all services
Services.register(dServices, oRestConf, Conf.get(('services', 'salt')))

# Init Templates
Templates.init('../templates')

# Create the HTTP server and map requests to service
REST.Server({
	"/customer/claim": {"methods": REST.CREATE | REST.DELETE | REST.UPDATE, "session": True},
	"/customer/dsid": {"methods": REST.READ, "session": True},
	"/customer/exists": {"methods": REST.READ, "session": True},
	"/customer/hide": {"methods": REST.UPDATE, "session": True},
	"/customer/id/byPhone": {"methods": REST.READ, "session": True},
	"/customer/messages": {"methods": REST.READ, "session": True},
	"/customer/mips": {"methods": REST.READ, "session": True},
	"/customer/mip/answer": {"methods": REST.UPDATE, "session": True},
	"/customer/name": {"methods": REST.READ, "session": True},
	"/customer/note": {"methods": REST.CREATE, "session": True},
	"/customer/notes": {"methods": REST.READ, "session": True},
	"/customer/shipping": {"methods": REST.READ, "session": True},

	"/message/incoming": {"methods": REST.CREATE},
	"/message/outgoing": {"methods": REST.CREATE, "session": True},
	"/msgs/claimed": {"methods": REST.READ, "session": True},
	"/msgs/claimed/new": {"methods": REST.READ, "session": True},
	"/msgs/search": {"methods": REST.READ, "session": True},
	"/msgs/search/customer": {"methods": REST.READ, "session": True},
	"/msgs/status": {"methods": REST.READ, "session": True},
	"/msgs/unclaimed": {"methods": REST.READ, "session": True},
	"/msgs/unclaimed/count": {"methods": REST.READ, "session": True},

	"/passwd/forgot": {"methods": REST.CREATE | REST.UPDATE},

	"/session": {"methods": REST.READ, "session": True},

	"/signin": {"methods": REST.POST},
	"/signout": {"methods": REST.POST, "session": True},

	"/stats/claimed": {"methods": REST.READ, "session": True},

	"/user": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
	"/user/active": {"methods": REST.UPDATE, "session": True},
	"/user/name": {"methods": REST.READ, "session": True},
	"/user/passwd": {"methods": REST.UPDATE, "session": True},
	"/users": {"methods": REST.READ, "session": True}

}, 'monolith', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['monolith']['host'],
	port=oRestConf['monolith']['port'],
	workers=oRestConf['monolith']['workers']
)
