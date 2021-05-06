# coding=utf8
""" HubSpot REST

Handles interactions with HubSpot
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-11-12"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.hubspot import HubSpot

# Local imports
from . import init

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		services={'hubspot':HubSpot()}
	)

	# Create the HTTP server and map requests to service
	REST.Server({
		"/customer/decline": {"methods": REST.UPDATE},
		"/customer/emails": {"methods": REST.READ, "session": True},
		"/customer/label": {"methods": REST.UPDATE}

	}, 'hubspot', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
		host=oRestConf['hubspot']['host'],
		port=oRestConf['hubspot']['port'],
		workers=oRestConf['hubspot']['workers'],
		timeout='timeout' in oRestConf['hubspot'] and oRestConf['hubspot']['timeout'] or 30
	)
