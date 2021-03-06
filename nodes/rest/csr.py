# coding=utf8
""" CSR REST

Handles CSR related activities
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-17"

# Pip imports
from RestOC import Conf, REST

# Service imports
from services.csr import CSR

# Local imports
from . import init, serviceError

# Only run if called directly
if __name__ == "__main__":

	# Init the REST info
	oRestConf = init(
		dbs=['primary'],
		services={'csr':CSR()},
		templates='templates'
	)

	# Create the HTTP server and map requests to service
	REST.Server({
		"/action": {"methods": REST.CREATE | REST.DELETE, "session": True},
		"/actions": {"methods": REST.READ, "session": True},

		"/agent": {"methods": REST.ALL, "session": True},
		"/agents": {"methods": REST.READ, "session": True},
		"/agent/hours": {"methods": REST.READ | REST.UPDATE, "session": True},
		"/agent/memo": {"methods": REST.CREATE, "session": True},
		"/agent/names": {"methods": REST.READ, "session": True},
		"/agent/names/transfer": {"methods": REST.READ, "session": True},
		"/agent/passwd": {"methods": REST.UPDATE, "session": True},
		"/agent/permissions": {"methods": REST.READ | REST.UPDATE, "session": True},

		"/lead/closed": {"methods": REST.UPDATE, "session": True},
		"/leads": {"methods": REST.READ, "session": True},

		"/list": {"methods": REST.CREATE | REST.UPDATE | REST.DELETE, "session": True},
		"/list/item": {"methods": REST.CREATE | REST.DELETE, "session": True},
		"/lists": {"methods": REST.READ, "session": True},

		"/patient/account": {"methods": REST.CREATE, "session": True},

		"/reminder": {"methods": REST.CREATE | REST.UPDATE | REST.DELETE, "session": True},
		"/reminder/resolve": {"methods": REST.UPDATE, "session": True},
		"/reminders": {"methods": REST.READ, "session": True},
		"/reminders/count": {"methods": REST.READ, "session": True},

		"/session": {"methods": REST.READ, "session": True},
		"/signin": {"methods": REST.CREATE},
		"/signout": {"methods": REST.CREATE},

		"/stats/totals": {"methods": REST.READ, "session": True},

		"/template/email": {"methods": REST.ALL, "session": True},
		"/template/emails": {"methods": REST.READ, "session": True},
		"/template/sms": {"methods": REST.ALL, "session": True},
		"/template/smss": {"methods": REST.READ, "session": True},

		"/ticket": {"methods": REST.ALL, "session": True},
		"/ticket/action": {"methods": REST.CREATE, "session": True},
		"/ticket/details": {"methods": REST.READ, "session": True},
		"/ticket/exists": {"methods": REST.READ},
		"/ticket/item": {"methods": REST.CREATE, "session": True},
		"/ticket/item/ids": {"methods": REST.READ, "session": True},
		"/ticket/open/user": {"methods": REST.READ, "session": True},
		"/ticket/resolve": {"methods": REST.UPDATE, "session": True},
		"/ticket/stats": {"methods": REST.READ, "session": True},
		"/ticket/stats/graph": {"methods": REST.READ, "session": True},
		"/ticket/stats/totals": {"methods": REST.READ, "session": True},
		"/tickets": {"methods": REST.READ, "session": True},
		"/tickets/customer": {"methods": REST.READ, "session": True},

		"/user": {"methods": REST.READ, "session": True}

		},
		'csr',
		"https?://(.*\\.)?%s" % Conf.get(("rest","allowed")).replace('.', '\\.'),
		error_callback=serviceError
	).run(
		host=oRestConf['csr']['host'],
		port=oRestConf['csr']['port'],
		workers=oRestConf['csr']['workers'],
		timeout='timeout' in oRestConf['csr'] and oRestConf['csr']['timeout'] or 30
	)
