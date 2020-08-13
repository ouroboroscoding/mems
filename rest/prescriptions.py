# coding=utf8
""" Prescriptions Service

Handles interactions with Prescriptions
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-10"

# Python imports
import os, platform

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL, REST, Services, Sesh, Templates

# App imports
from services.prescriptions import Prescriptions

# Load the config
Conf.load('config.json')
sConfOverride = 'config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add the global prepend and primary host to mysql
Record_Base.dbPrepend(Conf.get(("mysql", "prepend"), ''))
Record_MySQL.addHost('primary', Conf.get(("mysql", "hosts", "primary")))

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
	"monolith": None,
	"prescriptions": Prescriptions()
}

# Register all services
Services.register(dServices, oRestConf, Conf.get(('services', 'salt')))

# Init Templates
Templates.init('templates')

# Create the HTTP server and map requests to service
REST.Server({
	"/patient": {"methods": REST.READ, "session": True},
	"/patient/pharmacies": {"methods": REST.READ, "session": True},
	"/patient/pharmacy": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/patient/prescriptions": {"methods": REST.READ},
	"/patient/sso": {"methods": REST.READ, "session": True},

	"/pharmacy/fill/error": {"methods": REST.CREATE | REST.UPDATE | REST.DELETE, "session": True},
	"/pharmacy/fill/errors": {"methods": REST.READ, "session": True}

}, 'prescriptions', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['prescriptions']['host'],
	port=oRestConf['prescriptions']['port'],
	workers=oRestConf['prescriptions']['workers']
)