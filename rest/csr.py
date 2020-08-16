# coding=utf8
""" CSR Service

Handles CSR related activities
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-17"

# Python imports
import os, platform

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL, REST, Services, Sesh

# App imports
from services.csr import CSR

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
dServices = {k:None for k in Conf.get(('rest', 'services'))}
dServices['csr'] = CSR()

# Register all services
Services.register(dServices, oRestConf, Conf.get(('services', 'salt')))

# Create the HTTP server and map requests to service
REST.Server({
	"/agent": {"methods": REST.ALL, "session": True},
	"/agents": {"methods": REST.READ, "session": True},
	"/agent/internal": {"methods": REST.READ, "session": True},
	"/agent/names": {"methods": REST.READ, "session": True},
	"/agent/permissions": {"methods": REST.READ | REST.UPDATE, "session": True},

	"/list": {"methods": REST.CREATE | REST.UPDATE | REST.DELETE, "session": True},
	"/list/item": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/lists": {"methods": REST.READ, "session": True},

	"/template/email": {"methods": REST.ALL, "session": True},
	"/template/emails": {"methods": REST.READ, "session": True},
	"/template/sms": {"methods": REST.ALL, "session": True},
	"/template/smss": {"methods": REST.READ, "session": True}

}, 'csr', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['csr']['host'],
	port=oRestConf['csr']['port'],
	workers=oRestConf['csr']['workers']
)
