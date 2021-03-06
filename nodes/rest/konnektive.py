# coding=utf8
""" Konnektive REST

Handles interactions with Konnektive
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-09"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.konnektive import Konnektive

# Local imports
from . import init, serviceError

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'konnektive':Konnektive()}
	)

	# Create the HTTP server and map requests to service
	REST.Server({
		"/campaign": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
		"/campaigns": {"methods": REST.READ, "session": True},
		"/campaign/product": {"methods": REST.ALL, "session": True},
		"/campaign/products": {"methods": REST.READ, "session": True},
		"/customer": {"methods": REST.READ | REST.UPDATE, "session": True},
		"/customer/payment": {"methods": REST.UPDATE, "session": True, "environ": True},
		"/customer/purchases": {"methods": REST.READ, "session": True},
		"/customer/orders": {"methods": REST.READ, "session": True},
		"/customer/transactions": {"methods": REST.READ, "session": True},
		"/order": {"methods": REST.CREATE | REST.READ, "session": True, "environ": True},
		"/order/cancel": {"methods": REST.UPDATE, "session": True},
		"/order/qa": {"methods": REST.UPDATE, "session": True},
		"/order/refund": {"methods": REST.UPDATE, "session": True},
		"/order/transactions": {"methods": REST.READ, "session": True},
		"/purchase": {"methods": REST.READ, "session": True},
		"/purchase/cancel": {"methods": REST.UPDATE, "session": True},
		"/purchase/charge": {"methods": REST.UPDATE, "session": True},
		"/purchase/refund": {"methods": REST.UPDATE, "session": True}

		},
		'konnektive',
		"https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.'),
		error_callback=serviceError
	).run(
		host=oRestConf['konnektive']['host'],
		port=oRestConf['konnektive']['port'],
		workers=oRestConf['konnektive']['workers'],
		timeout='timeout' in oRestConf['konnektive'] and oRestConf['konnektive']['timeout'] or 30
	)
