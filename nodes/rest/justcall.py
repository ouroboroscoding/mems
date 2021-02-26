# coding=utf8
""" JustCall REST

Handles interactions with JustCall
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-02-22"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.justcall import JustCall

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	services={'justcall':JustCall()}
)

# Create the HTTP server and map requests to service
REST.Server({
	"/logs": {"methods": REST.READ, "session": True}

}, 'justcall', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['justcall']['host'],
	port=oRestConf['justcall']['port'],
	workers=oRestConf['justcall']['workers'],
	timeout='timeout' in oRestConf['justcall'] and oRestConf['justcall']['timeout'] or 30
)
