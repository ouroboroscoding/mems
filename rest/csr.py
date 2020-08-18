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

# Pip imports
from RestOC import Conf, REST

# App imports
from services.csr import CSR

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	dbs=['primary'],
	services={'csr':CSR()}
	templates='templates'
)

# Create the HTTP server and map requests to service
REST.Server({
	"/agent": {"methods": REST.ALL, "session": True},
	"/agents": {"methods": REST.READ, "session": True},
	"/agent/internal": {"methods": REST.READ, "session": True},
	"/agent/names": {"methods": REST.READ, "session": True},
	"/agent/passwd": {"methods": REST.UPDATE, "session": True},
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
