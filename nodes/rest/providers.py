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
REST.Server([

	{"uri": "/calendly/single", "methods": REST.READ | REST.DELETE, "session": False},
	{"uri": "/calendly/single", "methods": REST.CREATE, "session": True},

	{"uri": "/hours", "methods": REST.READ, "session": True},

	{"uri": "/product/to/rx", "methods": REST.CREATE, "session": True},
	{"uri": "/customer/to/rx", "methods": REST.UPDATE | REST.READ, "session": True},

	{"uri": "/prescriptions", "methods": REST.CREATE, "session": True},

	{"uri": "/provider", "methods": REST.ALL, "session": True},
	{"uri": "/providers", "methods": REST.READ, "session": True},
	{"uri": "/provider/internal", "methods": REST.READ, "session": True},
	{"uri": "/provider/memo", "methods": REST.CREATE, "session": True},
	{"uri": "/provider/names", "methods": REST.READ, "session": True},
	{"uri": "/provider/passwd", "methods": REST.UPDATE, "session": True},
	{"uri": "/provider/permissions", "methods": REST.READ | REST.UPDATE, "session": True},
	{"uri": "/provider/tracking", "methods": REST.READ, "session": True},
	{"uri": "/roundrobin", "methods": REST.READ, "session": True},

	{"uri": "/request", "methods": REST.CREATE, "session": True},

	{"uri": "/session", "methods": REST.READ, "session": True},
	{"uri": "/signin", "methods": REST.CREATE},
	{"uri": "/signout", "methods": REST.CREATE, "session": True},

	{"uri": "/template", "methods": REST.ALL, "session": True},
	{"uri": "/templates", "methods": REST.READ, "session": True},

	{"uri": "/tracking", "methods": REST.CREATE, "session": True}


], 'providers', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['providers']['host'],
	port=oRestConf['providers']['port'],
	workers=oRestConf['providers']['workers'],
	timeout='timeout' in oRestConf['providers'] and oRestConf['providers']['timeout'] or 30
)
