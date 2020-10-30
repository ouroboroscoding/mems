# coding=utf8
""" Monolith Service

Handles everything in the old memo system
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-04-26"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.monolith import Monolith

# Local imports
from . import init

# Init the REST info
oRestConf = init(
	dbs=['monolith'],
	services={'monolith':Monolith()},
	templates='templates'
)

# Create the HTTP server and map requests to service
REST.Server({

	"/customer/calendly": {"methods": REST.READ, "session": True},
	"/customer/claim": {"methods": REST.CREATE | REST.UPDATE | REST.DELETE, "session": True},
	"/customer/claim/clear": {"methods": REST.UPDATE, "session": True},
	"/customer/dob": {"methods": REST.READ, "session": True},
	"/customer/dsid": {"methods": REST.READ, "session": True},
	"/customer/exists": {"methods": REST.READ, "session": True},
	"/customer/hide": {"methods": REST.UPDATE, "session": True},
	"/customer/hrtLabs": {"methods": REST.READ, "session": True},
	"/customer/id/byPhone": {"methods": REST.READ, "session": True},
	"/customer/messages": {"methods": REST.READ, "session": True},
	"/customer/mip": {"methods": REST.READ, "session": True},
	"/customer/mips": {"methods": REST.READ, "session": True},
	"/customer/mip/answer": {"methods": REST.UPDATE, "session": True},
	"/customer/name": {"methods": REST.READ, "session": True},
	"/customer/note": {"methods": REST.CREATE, "session": True},
	"/customer/notes": {"methods": REST.READ, "session": True},
	"/customer/shipping": {"methods": REST.READ, "session": True},
	"/customer/stop": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/customer/stops": {"methods": REST.READ, "session": True},

	"/message/incoming": {"methods": REST.CREATE},
	"/message/outgoing": {"methods": REST.CREATE},
	"/msgs/claimed": {"methods": REST.READ, "session": True},
	"/msgs/claimed/new": {"methods": REST.READ, "session": True},
	"/msgs/search": {"methods": REST.READ, "session": True},
	"/msgs/search/customer": {"methods": REST.READ, "session": True},
	"/msgs/status": {"methods": REST.READ, "session": True},
	"/msgs/unclaimed": {"methods": REST.READ, "session": True},
	"/msgs/unclaimed/count": {"methods": REST.READ, "session": True},

	"/order/claim": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/order/claimed": {"methods": REST.READ, "session": True},

	"/orders/pending/csr": {"methods": REST.READ, "session": True},
	"/orders/pending/csr/count": {"methods": REST.READ, "session": True},
	"/orders/pending/provider/ed": {"methods": REST.READ, "session": True},
	"/orders/pending/provider/hrt": {"methods": REST.READ, "session": True},

	"/passwd/forgot": {"methods": REST.CREATE | REST.UPDATE},

	"/pharmacy/fill/error": {"methods": REST.UPDATE | REST.DELETE, "session": True},
	"/pharmacy/fill/errors": {"methods": REST.READ, "session": True},

	"/provider/calendly": {"methods": REST.READ, "session": True},

	"/signin": {"methods": REST.POST},

	"/stats/claimed": {"methods": REST.READ, "session": True},

	"/user": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
	"/users": {"methods": REST.READ, "session": True},
	"/user/active": {"methods": REST.UPDATE, "session": True},
	"/user/name": {"methods": REST.READ, "session": True},
	"/user/passwd": {"methods": REST.UPDATE, "session": True}

}, 'monolith', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['monolith']['host'],
	port=oRestConf['monolith']['port'],
	workers=oRestConf['monolith']['workers'],
	timeout='timeout' in oRestConf['monolith'] and oRestConf['monolith']['timeout'] or 30
)
