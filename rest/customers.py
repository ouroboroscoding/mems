# coding=utf8
""" Customers Service

Handles Customer related activities
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-10-18"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.customers import Customers

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	dbs=['primary'],
	services={'customers':Customers()}
)

# Create the HTTP server and map requests to service
REST.Server({

	"/address": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
	"/customer": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
	"/customer/addresses": {"methods": REST.READ, "session": True},
	"/customer/notes": {"methods": REST.READ, "session": True},
	"/note": {"methods": REST.CREATE, "session": True}

}, 'customers', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['customers']['host'],
	port=oRestConf['customers']['port'],
	workers=oRestConf['customers']['workers'],
	timeout='timeout' in oRestConf['customers'] and oRestConf['customers']['timeout'] or 30
)
