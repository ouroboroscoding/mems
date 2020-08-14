# coding=utf8
"""Trigger

Runs through the trigger process to see if any error came up
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-13"

# Python imports
import os
import platform
import sys

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL, REST, Services

# Cron imports
from crons.shared import PharmacyFill

# If the version argument is missing
if len(sys.argv) < 3:
	print('Must specify the type, id, and order:\n\tpython -m tools.trigger knk 285168 95AC0F4D96')
	sys.exit(1)

# Load the config
Conf.load('config.json')
sConfOverride = 'config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add the global prepend and primary host to mysql
Record_Base.dbPrepend(Conf.get(("mysql", "prepend"), ''))
Record_MySQL.addHost('primary', Conf.get(("mysql", "hosts", "primary")))
Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))

# Register all services
Services.register({
		'auth':None,
		'prescriptions':None
	},
	REST.Config(Conf.get("rest")),
	Conf.get(('services', 'salt'))
)

# Init PharmacyFill
PharmacyFill.initialise()

# Try to process the record
dRes = PharmacyFill.process({
	"crm_type": sys.argv[1],
	"crm_id": sys.argv[2],
	"crm_order": sys.argv[3]
})

# Print the result
print('Status: %s' % (dRes['status'] and 'Success' or 'Failure'))
print('Data: %s' % dRes['data'])
