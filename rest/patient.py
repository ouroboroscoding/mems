# coding=utf8
""" Patient Service

Handles patient access
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-06-26"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.patient import Patient

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	dbs=['primary'],
	services={'patient':Patient()},
	templates='templates'
)

# Create the HTTP server and map requests to service
REST.Server({

	"/account": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
	"/account/byCRM": {"methods": REST.READ, "session": True},
	"/account/email": {"methods": REST.UPDATE, "session": True},
	"/account/forgot": {"methods": REST.CREATE | REST.UPDATE},
	"/account/rx": {"methods": REST.UPDATE, "session": True},
	"/account/verify": {"methods": REST.UPDATE},

	"/session": {"methods": REST.READ, "session": True},

	"/setup/start": { "methods": REST.CREATE, "session": True},
	"/setup/validate": { "methods": REST.CREATE},

	"/signin": {"methods": REST.POST},
	"/signout": {"methods": REST.POST, "session": True},

	"/support_request": {"methods": REST.CREATE, "session": True}

}, 'patient', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['patient']['host'],
	port=oRestConf['patient']['port'],
	workers=oRestConf['patient']['workers']
)
