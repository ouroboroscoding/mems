# coding=utf8
""" Konnektive Service

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

# App imports
from services.konnektive import Konnektive

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	services={'konnektive':Konnektive()}
)

# Create the HTTP server and map requests to service
REST.Server({
	"/customer": {"methods": REST.READ | REST.UPDATE, "session": True},
	"/customer/purchases": {"methods": REST.READ, "session": True},
	"/customer/orders": {"methods": REST.READ, "session": True},
	"/customer/transactions": {"methods": REST.READ, "session": True},
	"/order/transactions": {"methods": REST.READ, "session": True}

}, 'konnektive', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['konnektive']['host'],
	port=oRestConf['konnektive']['port'],
	workers=oRestConf['konnektive']['workers']
)
