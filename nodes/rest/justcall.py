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
from . import init, serviceError

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'justcall':JustCall()}
	)

	# Create the HTTP server and map requests to service
	REST.Server({

		"/agent/memo": {"methods": REST.READ | REST.UPDATE, "session": True},

		"/details": {"methods": REST.READ},

		"/log": {"methods": REST.READ},
		"/logs": {"methods": REST.READ, "session": True},

		"/queue": {"methods": REST.READ | REST.CREATE | REST.DELETE},

		"/queue/number": {"methods": REST.READ | REST.CREATE | REST.DELETE, "session": True},

		"/users": {"methods": REST.READ, "session": True}

		},
		'justcall',
		"https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.'),
		error_callback=serviceError
	).run(
		host=oRestConf['justcall']['host'],
		port=oRestConf['justcall']['port'],
		workers=oRestConf['justcall']['workers'],
		timeout='timeout' in oRestConf['justcall'] and oRestConf['justcall']['timeout'] or 30
	)
