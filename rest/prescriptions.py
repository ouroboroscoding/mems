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

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.prescriptions import Prescriptions

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	dbs=['primary'],
	services={'prescriptions':Prescriptions()}
)

# Create the HTTP server and map requests to service
REST.Server({
	"/patient": {"methods": REST.CREATE | REST.READ, "session": True},
	"/patient/pharmacies": {"methods": REST.READ, "session": True},
	"/patient/pharmacy": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/patient/prescriptions": {"methods": REST.READ},
	"/patient/sso": {"methods": REST.READ, "session": True},

	"/pharmacy/fill": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/pharmacy/fill/byCustomer": {"methods": REST.READ, "session": True},

	"/pharmacy/fill/error": {"methods": REST.CREATE | REST.UPDATE | REST.DELETE, "session": True},
	"/pharmacy/fill/errors": {"methods": REST.READ, "session": True}

}, 'prescriptions', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['prescriptions']['host'],
	port=oRestConf['prescriptions']['port'],
	workers=oRestConf['prescriptions']['workers'],
	timeout='timeout' in oRestConf['prescriptions'] and oRestConf['prescriptions']['timeout'] or 30
)
