# coding=utf8
""" Konnektive Service

Handles interactions with Konnektive
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-09"

# Python imports
import os, platform

# Pip imports
from RestOC import Conf, REST, Services, Sesh, Templates

# App imports
from services.konnektive import Konnektive

# Load the config
Conf.load('../config.json')
sConfOverride = '../config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

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
	"konnektive": Konnektive()
}

# Register all services
Services.register(dServices, oRestConf, Conf.get(('services', 'salt')))

# Init Templates
Templates.init('../templates')

# Create the HTTP server and map requests to service
REST.Server({
	"/customer": {"methods": REST.READ | REST.UPDATE, "session": True},
	"/customer/orders": {"methods": REST.READ, "session": True},
	"/customer/transactions": {"methods": REST.READ, "session": True},
	"/order/transactions": {"methods": REST.READ, "session": True}

}, 'konnektive', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['konnektive']['host'],
	port=oRestConf['konnektive']['port'],
	workers=oRestConf['konnektive']['workers']
)
