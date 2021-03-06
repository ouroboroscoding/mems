# coding=utf8
""" Reports REST

Handles Report related activities
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-18"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.reports import Reports

# Local imports
from . import init, serviceError

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'reports':Reports()}
	)

	# Create the HTTP server and map requests to service
	REST.Server({

		"/recipients": {"methods": REST.ALL, "session": True},
		"/recipients/internal": {"methods": REST.READ}

		},
		'reports',
		"https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.'),
		error_callback=serviceError
	).run(
		host=oRestConf['reports']['host'],
		port=oRestConf['reports']['port'],
		workers=oRestConf['reports']['workers'],
		timeout='timeout' in oRestConf['reports'] and oRestConf['reports']['timeout'] or 30
	)
