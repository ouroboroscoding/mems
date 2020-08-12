# coding=utf8
""" Web Poll Service

Handles web polling (websocket)
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2019-03-29"

# Python imports
import os, platform

# Framework imports
from RestOC import Conf, REST, Services, Sesh

# App imports
from services.webpoll import WebPoll

# Load the config
Conf.load('config.json')
sConfOverride = 'config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Init the Sesh module
Sesh.init(Conf.get(("redis", "primary")))

# Create the REST config instance
oRestConf = REST.Config(Conf.get("rest"))

# Set verbose mode if requested
if 'VERBOSE' in os.environ and os.environ['VERBOSE'] == '1':
	Services.verbose()

# Register all necessary services
Services.register({
	"auth": None,
	"webpoll": WebPoll()
}, oRestConf, Conf.get(('services', 'salt')))

# Create the HTTP server and map requests to service
REST.Server({
	"/clear": {"methods": REST.UPDATE, "session": True},
	"/join": {"methods": REST.CREATE, "session": True},
	"/leave": {"methods": REST.CREATE, "session": True},
	"/pull": {"methods": REST.READ, "session": True},
	"/websocket": {"methods": REST.READ, "session": True}

}, 'webpoll', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['webpoll']['host'],
	port=oRestConf['webpoll']['port'],
	workers=oRestConf['webpoll']['workers']
)
