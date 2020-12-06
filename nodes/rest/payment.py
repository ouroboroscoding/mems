# coding=utf8
""" Payment REST

Handles interactions with Payment
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-11"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.payment import Payment

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	dbs=['primary'],
	services={'payment':Payment()},
	templates='templates'
)

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
	workers=oRestConf['payment']['workers'],
	timeout='timeout' in oRestConf['payment'] and oRestConf['payment']['timeout'] or 30
)
