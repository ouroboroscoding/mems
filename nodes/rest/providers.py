# coding=utf8
""" Providers REST

Handles Providers related activities
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-10-15"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.providers import Providers

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	dbs=['primary'],
	services={'providers':Providers()},
	templates='templates'
)

# Create the HTTP server and map requests to service
REST.Server({
	"/customer/to/rx": {"methods": REST.UPDATE | REST.READ, "session": True},

	"/provider": {"methods": REST.ALL, "session": True},
	"/providers": {"methods": REST.READ, "session": True},
	"/provider/internal": {"methods": REST.READ, "session": True},
	"/provider/memo": {"methods": REST.CREATE, "session": True},
	"/provider/names": {"methods": REST.READ, "session": True},
	"/provider/passwd": {"methods": REST.UPDATE, "session": True},
	"/provider/permissions": {"methods": REST.READ | REST.UPDATE, "session": True},

	"/roundrobin": {"methods": REST.READ, "session": True},

	"/session": {"methods": REST.READ, "session": True},
	"/signin": {"methods": REST.CREATE},
	"/signout": {"methods": REST.CREATE},

	"/template": {"methods": REST.ALL, "session": True},
	"/templates": {"methods": REST.READ, "session": True},

	"/tracking": {"methods": REST.CREATE, "session": True}

}, 'providers', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['providers']['host'],
	port=oRestConf['providers']['port'],
	workers=oRestConf['providers']['workers'],
	timeout='timeout' in oRestConf['providers'] and oRestConf['providers']['timeout'] or 30
)
