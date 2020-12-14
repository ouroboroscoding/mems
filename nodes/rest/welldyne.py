# coding=utf8
""" WellDyne REST

Handles everything associated with WellDyneRx
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-07-01"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.welldyne import WellDyne

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	dbs=['primary', 'monolith'],
	services={'welldyne':WellDyne()}
)

# Create the HTTP server and map requests to service
REST.Server({

	"/adhoc": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/adhoc/manual": {"methods": REST.READ | REST.DELETE, "session": True},
	"/adhocs": {"methods": REST.READ, "session": True},

	"/never/started": {"methods": REST.DELETE, "session": True},
	"/never/started/poll": {"methods": REST.UPDATE, "session": True},
	"/never/started/ready": {"methods": REST.UPDATE, "session": True},
	"/never/starteds": {"methods": REST.READ, "session": True},

	"/outbound/adhoc": {"methods": REST.UPDATE, "session": True},
	"/outbound/ready": {"methods": REST.UPDATE, "session": True},
	"/outbounds": {"methods": REST.READ, "session": True},

	"/postback": {"methods": REST.CREATE, "environ": True},

	"/stats": {"methods": REST.READ, "session": True},

	"/trigger/info": {"methods": REST.READ, "session": True}

}, 'welldyne', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['welldyne']['host'],
	port=oRestConf['welldyne']['port'],
	workers=oRestConf['welldyne']['workers'],
	timeout='timeout' in oRestConf['welldyne'] and oRestConf['welldyne']['timeout'] or 30
)
