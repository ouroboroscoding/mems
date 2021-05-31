# coding=utf8
""" Qualified Medication REST

Handles Qualified Medication related activities
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-10-12"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.qualmed import QualMed

# Local imports
from . import init, serviceError

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'qualmed':QualMed()}
	)

	# Create the HTTP server and map requests to service
	REST.Server({

		"/item": {"methods": REST.ALL, "session": True},
		"/items": {"methods": REST.READ, "session": True}

		},
		'qualmed',
		"https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.'),
		error_callback=serviceError
	).run(
		host=oRestConf['qualmed']['host'],
		port=oRestConf['qualmed']['port'],
		workers=oRestConf['qualmed']['workers'],
		timeout='timeout' in oRestConf['qualmed'] and oRestConf['qualmed']['timeout'] or 30
	)
