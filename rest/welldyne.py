# coding=utf8
""" WellDyne Service

Handles everything associated with WellDyneRx
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-07-01"

# Python imports
import os, platform

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL, REST, \
					Services, Sesh, Templates

# App imports
from services.welldyne import WellDyne

# Load the config
Conf.load('config.json')
sConfOverride = 'config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add the global prepend and primary host to mysql
Record_Base.dbPrepend(Conf.get(("mysql", "prepend"), ''))
Record_MySQL.addHost('primary', Conf.get(("mysql", "hosts", "primary")))
Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))

# Init the Sesh module
Sesh.init(Conf.get(("redis", "primary")))

# Create the REST config instance
oRestConf = REST.Config(Conf.get("rest"))

# Set verbose mode if requested
if 'VERBOSE' in os.environ and os.environ['VERBOSE'] == '1':
	Services.verbose()

# Get all the services
dServices = {
	"auth": None,
	"communications": None,
	"monolith": None,
	"welldyne": WellDyne()
}

# Register all services
Services.register(dServices, oRestConf, Conf.get(('services', 'salt')))

# Init Templates
Templates.init('templates')

# Create the HTTP server and map requests to service
REST.Server({

	"/adhoc": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/adhoc/manual": {"methods": REST.READ | REST.DELETE, "session": True},
	"/adhocs": {"methods": REST.READ, "session": True},

	"/outbound/adhoc": {"methods": REST.UPDATE, "session": True},
	"/outbound/ready": {"methods": REST.UPDATE, "session": True},
	"/outbounds": {"methods": REST.READ, "session": True},

	"/stats": {"methods": REST.READ, "session": True},

	"/trigger/info": {"methods": REST.READ, "session": True}

}, 'welldyne', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['welldyne']['host'],
	port=oRestConf['welldyne']['port'],
	workers=oRestConf['welldyne']['workers']
)
