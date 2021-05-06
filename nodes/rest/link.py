# coding=utf8
""" Link REST

Handles link shortening service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-03-08"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.link import Link

# Local imports
from . import init

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'link':Link()}
	)

	# Create the HTTP server and map requests to service
	REST.Server([

		# Public
		{"uri": "/stats", "methods": REST.READ},

		{"uri": "/view", "methods": REST.CREATE},

		# Private
		{"uri": "/url", "methods": REST.CREATE | REST.DELETE, "session": True},

		{"uri": "/urls", "methods": REST.READ, "session": True}

	], 'link', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
		host=oRestConf['link']['host'],
		port=oRestConf['link']['port'],
		workers=oRestConf['link']['workers'],
		timeout='timeout' in oRestConf['link'] and oRestConf['link']['timeout'] or 30
	)
