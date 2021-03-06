# coding=utf8
""" Web Poll REST

Handles web polling (websocket)
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2019-03-29"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.webpoll import WebPoll

# Local imports
from . import init, serviceError

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		services={'webpoll':WebPoll()}
	)

	# Create the HTTP server and map requests to service
	REST.Server({
		"/clear": {"methods": REST.UPDATE, "session": True},
		"/join": {"methods": REST.CREATE, "session": True},
		"/leave": {"methods": REST.CREATE, "session": True},
		"/pull": {"methods": REST.READ, "session": True},
		"/websocket": {"methods": REST.READ, "session": True}

		},
		'webpoll',
		"https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.'),
		error_callback=serviceError
	).run(
		host=oRestConf['webpoll']['host'],
		port=oRestConf['webpoll']['port'],
		workers=oRestConf['webpoll']['workers'],
		timeout='timeout' in oRestConf['webpoll'] and oRestConf['webpoll']['timeout'] or 30
	)
