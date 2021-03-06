# coding=utf8
""" Products REST

Handles Product related activities
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-10-08"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.products import Products

# Local imports
from . import init, serviceError

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'products':Products()}
	)

	# Create the HTTP server and map requests to service
	REST.Server({

		"/group": {"methods": REST.CREATE | REST.UPDATE, "session": True},
		"/groups": {"methods": REST.READ, "session": True},
		"/medication": {"methods": REST.CREATE | REST.UPDATE, "session": True},
		"/medications": {"methods": REST.READ, "session": True},
		"/product": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
		"/products": {"methods": REST.READ, "session": True}

		},
		'products',
		"https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.'),
		error_callback=serviceError
	).run(
		host=oRestConf['products']['host'],
		port=oRestConf['products']['port'],
		workers=oRestConf['products']['workers'],
		timeout='timeout' in oRestConf['products'] and oRestConf['products']['timeout'] or 30
	)
