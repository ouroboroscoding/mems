# coding=utf8
""" Auth Service

Handles logins and letting them sign in/out
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-03-29"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.auth import Auth

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	dbs=['primary'],
	services={'auth':Auth()},
	templates='templates'
)

# Create the HTTP server and map requests to service
REST.Server({

	"/permissions": {"methods": REST.READ | REST.UPDATE, "session": True},
	"/permissions/self": {"methods": REST.READ, "session": True},

	"/rights/verify": {"methods": REST.READ, "session": True},

	"/search": {"methods": REST.READ, "session": True},

	"/session": {"methods": REST.READ, "session": True},

	"/signin": {"methods": REST.POST},
	"/signout": {"methods": REST.POST, "session": True},

	"/user": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
	"/user/email": {"methods": REST.UPDATE, "session": True},
	"/user/names": {"methods": REST.READ, "session": True},
	"/user/passwd": {"methods": REST.UPDATE, "session": True},
	"/user/passwd/forgot": {"methods": REST.CREATE | REST.UPDATE}

}, 'auth', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['auth']['host'],
	port=oRestConf['auth']['port'],
	workers=oRestConf['auth']['workers'],
	timeout='timeout' in oRestConf['auth'] and oRestConf['auth']['timeout'] or 30
)
