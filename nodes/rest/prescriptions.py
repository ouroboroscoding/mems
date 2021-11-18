# coding=utf8
""" Prescriptions REST

Handles interactions with Prescriptions
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-10"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.prescriptions import Prescriptions

# Local imports
from . import init, serviceError

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'prescriptions':Prescriptions()}
	)

	# Create the HTTP server and map requests to service
	REST.Server({
		"/ds/dispenseunits": {"methods": REST.READ, "session": True},
		"/ds/pharmacies": {"methods": REST.READ, "session": True},

		"/diagnoses": {"methods": REST.READ, "session": True},
		"/diagnosis": {"methods": REST.ALL, "session": True},
		"/diagnosis/lookup": {"methods": REST.READ, "session": True},


		"/hrt/order": {"methods": REST.DELETE, "session": True},
		"/hrt/order/claim": {"methods": REST.UPDATE, "session": True},
		"/hrt/order/complete": {"methods": REST.UPDATE, "session": True},
		"/hrt/order/flag": {"methods": REST.UPDATE, "session": True},
		"/hrt/order/incomplete": {"methods": REST.READ, "session": True},
		"/hrt/order/incomplete/count": {"methods": REST.READ, "session": True},
		"/hrt/order/search": {"methods": REST.READ, "session": True},
		"/hrt/order/ticket": {"methods": REST.UPDATE, "session": True},

		"/patient": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
		"/patient/medications": {"methods": REST.READ, "session": True},
		"/patient/pharmacies": {"methods": REST.READ, "session": True},
		"/patient/pharmacy": {"methods": REST.CREATE | REST.DELETE, "session": True},
		"/patient/prescription": {"methods": REST.CREATE | REST.READ, "session": True},
		"/patient/prescriptions": {"methods": REST.READ},
		"/patient/sso": {"methods": REST.READ, "session": True},

		"/pharmacies": {"methods": REST.READ, "session": True},

		"/pharmacy/fill": {"methods": REST.CREATE | REST.DELETE, "session": True},
		"/pharmacy/fill/byCustomer": {"methods": REST.READ, "session": True},

		"/pharmacy/fill/error": {"methods": REST.CREATE | REST.UPDATE | REST.DELETE, "session": True},
		"/pharmacy/fill/errors": {"methods": REST.READ, "session": True},

		"/product": {"methods": REST.ALL, "session": True},
		"/products": {"methods": REST.READ, "session": True},

		"/provider/notifications": {"methods": REST.READ, "session": True},
		"/provider/sso": {"methods": REST.READ, "session": True}

		},
		'prescriptions',
		"https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.'),
		error_callback=serviceError
	).run(
		host=oRestConf['prescriptions']['host'],
		port=oRestConf['prescriptions']['port'],
		workers=oRestConf['prescriptions']['workers'],
		timeout='timeout' in oRestConf['prescriptions'] and oRestConf['prescriptions']['timeout'] or 30
	)
