# coding=utf8
""" Monolith REST

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

	"/agent/claim": {"methods": REST.DELETE, "session": True},
	"/agent/claims": {"methods": REST.READ, "session": True},

	"/calendly/event": {"methods": REST.ALL, "session": True},
	"/calendly/events": {"methods": REST.READ, "session": True},

	"/customer/calendly": {"methods": REST.READ, "session": True},
	"/customer/claim": {"methods": REST.CREATE | REST.UPDATE | REST.DELETE, "session": True},
	"/customer/claim/view": {"methods": REST.UPDATE, "session": True},
	"/customer/dob": {"methods": REST.READ, "session": True},
	"/customer/dsid": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
	"/customer/everify": {"methods": REST.READ | REST.UPDATE, "session": True},
	"/customer/exists": {"methods": REST.READ, "session": True},
	"/customer/hide": {"methods": REST.UPDATE, "session": True},
	"/customer/hrt": {"methods": REST.READ | REST.UPDATE, "session": True},
	"/customer/hrt/lab": {"methods": REST.CREATE, "session": True},
	"/customer/hrt/labs": {"methods": REST.READ, "session": True},
	"/customer/hrt/symptoms": {"methods": REST.READ, "session": True},
	"/customer/id/byPhone": {"methods": REST.READ, "session": True},
	"/customer/messages": {"methods": REST.READ, "session": True},
	"/customer/messages/incoming": {"methods": REST.READ, "session": True},
	"/customer/mip": {"methods": REST.READ, "session": True},
	"/customer/mips": {"methods": REST.READ, "session": True},
	"/customer/mip/answer": {"methods": REST.UPDATE, "session": True},
	"/customer/name": {"methods": REST.READ, "session": True},
	"/customer/note": {"methods": REST.CREATE, "session": True},
	"/customer/notes": {"methods": REST.READ, "session": True},
	"/customer/search": {"methods": REST.READ, "session": True},
	"/customer/shipping": {"methods": REST.READ, "session": True},
	"/customer/stop": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/customer/stops": {"methods": REST.READ, "session": True},
	"/customer/provider/return": {"methods": REST.UPDATE, "session": True},
	"/customer/provider/transfer": {"methods": REST.UPDATE, "session": True},
	"/customer/providers": {"methods": REST.READ, "session": True},

	"/encounter": {"methods": REST.READ},

	"/hrt/dropped/reasons": {"methods": REST.READ, "session": True},
	"/hrt/stats": {"methods": REST.READ, "session": True},
	"/hrt/patients": {"methods": REST.READ, "session": True},

	"/internal/customersWithClaimed": {"methods": REST.READ, "session": True},
	"/internal/ticketInfo": {"methods": REST.READ},

	"/message/incoming": {"methods": REST.CREATE},
	"/message/outgoing": {"methods": REST.CREATE},
	"/msgs/claimed": {"methods": REST.READ, "session": True},
	"/msgs/claimed/new": {"methods": REST.READ, "session": True},
	"/msgs/search": {"methods": REST.READ, "session": True},
	"/msgs/search/customer": {"methods": REST.READ, "session": True},
	"/msgs/status": {"methods": REST.READ, "session": True},
	"/msgs/unclaimed": {"methods": REST.READ, "session": True},
	"/msgs/unclaimed/count": {"methods": REST.READ, "session": True},

	"/notes/new": {"methods": REST.READ, "session": True},

	"/order/approve": {"methods": REST.UPDATE, "session": True},
	"/order/decline": {"methods": REST.UPDATE, "session": True},
	"/order/claim": {"methods": REST.CREATE | REST.DELETE, "session": True},
	"/order/claim/view": {"methods": REST.UPDATE, "session": True},
	"/order/claimed": {"methods": REST.READ, "session": True},
	"/order/continuous": {"methods": REST.CREATE | REST.READ, "session": True},
	"/order/continuous/approve": {"methods": REST.UPDATE, "session": True},
	"/order/continuous/cancel": {"methods": REST.UPDATE, "session": True},
	"/order/continuous/decline": {"methods": REST.UPDATE, "session": True},
	"/order/label": {"methods": REST.UPDATE, "session": True},
	"/order/refresh": {"methods": REST.UPDATE, "session": True},
	"/order/transfer": {"methods": REST.UPDATE, "session": True},

	"/orders/pending/counts": {"methods": REST.READ, "session": True},
	"/orders/pending/csr": {"methods": REST.READ, "session": True},
	"/orders/pending/csr/count": {"methods": REST.READ, "session": True},
	"/orders/pending/provider/ed": {"methods": REST.READ, "session": True},
	"/orders/pending/provider/ed/cont": {"methods": REST.READ, "session": True},
	"/orders/pending/provider/hrt": {"methods": REST.READ, "session": True},
	"/orders/pending/provider/hrt/cont": {"methods": REST.READ, "session": True},

	"/passwd/forgot": {"methods": REST.CREATE | REST.UPDATE},

	"/phone/change": {"methods": REST.UPDATE, "session": True},

	"/provider/calendly": {"methods": REST.READ, "session": True},
	"/provider/claim": {"methods": REST.DELETE, "session": True},
	"/provider/claims": {"methods": REST.READ, "session": True},
	"/provider/sms": {"methods": REST.CREATE, "session": True},

	"/providers": {"methods": REST.READ, "session": True},

	"/signin": {"methods": REST.POST},

	"/stats/claimed": {"methods": REST.READ, "session": True},

	"/user": {"methods": REST.CREATE | REST.READ | REST.UPDATE, "session": True},
	"/users": {"methods": REST.READ, "session": True},
	"/user/active": {"methods": REST.UPDATE, "session": True},
	"/user/id": {"methods": REST.READ},
	"/user/name": {"methods": REST.READ, "session": True},
	"/user/passwd": {"methods": REST.UPDATE, "session": True},

	"/workflow": {"methods": REST.POST}

}, 'monolith', "https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.')).run(
	host=oRestConf['monolith']['host'],
	port=oRestConf['monolith']['port'],
	workers=oRestConf['monolith']['workers'],
	timeout='timeout' in oRestConf['monolith'] and oRestConf['monolith']['timeout'] or 30
)
