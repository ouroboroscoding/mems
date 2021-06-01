# coding=utf8
""" Patient REST

Handles patient access
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-06-26"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.patient import Patient

# Local imports
from . import init, serviceError

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'patient':Patient()},
		templates='templates'
	)

	# Create the HTTP server and map requests to service
	REST.Server({

		"/account": {"methods": REST.CREATE | REST.READ, "session": True},
		"/account/byCRM": {"methods": REST.READ, "session": True},
		"/account/email": {"methods": REST.UPDATE, "session": True},
		"/account/forgot": {"methods": REST.CREATE | REST.UPDATE},
		"/account/payment": {"methods": REST.UPDATE, "session": True},
		"/account/phone": {"methods": REST.UPDATE, "session": True},
		"/account/rx": {"methods": REST.UPDATE, "session": True},
		"/account/verify": {"methods": REST.UPDATE},

		"/session": {"methods": REST.READ, "session": True},

		"/setup/attempts": {"methods": REST.READ, "session": True},
		"/setup/reset": {"methods": REST.UPDATE, "session": True},
		"/setup/start": {"methods": REST.CREATE, "session": True},
		"/setup/update": {"methods": REST.UPDATE, "session": True},
		"/setup/validate": {"methods": REST.CREATE},

		"/signin": {"methods": REST.POST, "environ": True},
		"/signout": {"methods": REST.POST, "session": True},

		"/support_request": {"methods": REST.CREATE, "session": True}

		},
		'patient',
		"https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.'),
		error_callback=serviceError
	).run(
		host=oRestConf['patient']['host'],
		port=oRestConf['patient']['port'],
		workers=oRestConf['patient']['workers'],
		timeout='timeout' in oRestConf['patient'] and oRestConf['patient']['timeout'] or 30
	)
