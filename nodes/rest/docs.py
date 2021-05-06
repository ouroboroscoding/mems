# coding=utf8
""" Docs REST

Handles documentation
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-02-06"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.docs import Docs

# Local imports
from . import init

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'docs':Docs()}
	)

	# Create the HTTP server and map requests to service
	REST.Server([

		# Public
		{"uri": "/errors", "methods": REST.READ},

		{"uri": "/noun", "methods": REST.READ},

		{"uri": "/service", "methods": REST.READ},
		{"uri": "/services", "methods": REST.READ},

		# Private
		{"uri": "/error", "methods": REST.CREATE | REST.DELETE | REST.UPDATE, "session": True},

		{"uri": "/noun", "methods": REST.CREATE | REST.DELETE | REST.UPDATE, "session": True},

		{"uri": "/service", "methods": REST.CREATE | REST.DELETE | REST.UPDATE, "session": True}

	], 'docs', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
		host=oRestConf['docs']['host'],
		port=oRestConf['docs']['port'],
		workers=oRestConf['docs']['workers'],
		timeout='timeout' in oRestConf['docs'] and oRestConf['docs']['timeout'] or 30
	)
