# coding=utf8
"""Reports

Handles setting up report scripts
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-19"

# Python imports
import importlib
import os
import platform
import sys

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL, REST, Services

# Load the config
Conf.load('../config.json')
sConfOverride = '../config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add the global prepend and primary host to mysql
Record_Base.dbPrepend(Conf.get(("mysql", "prepend"), ''))
Record_MySQL.addHost('primary', Conf.get(("mysql", "hosts", "primary")))
Record_MySQL.addHost('payment', Conf.get(("mysql", "hosts", "payment")))
Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))
Record_MySQL.addHost('monolith_prod', Conf.get(("mysql", "hosts", "monolith_prod")))

# Register all services
Services.register(
	{k:None for k in Conf.get(('rest', 'services'))},
	REST.Config(Conf.get("rest")),
	Conf.get(('services', 'salt'))
)

# Store the report
sReport = sys.argv[1]

# Try to import the cron
try:
	oReport = importlib.import_module('reports.%s' % sReport)
except ImportError as e:
	print('The given report "%s" is invalid.' % sReport)
	print(e)
	sys.exit(1)

# Run the cron with whatever additional arguments were passed
sys.exit(oReport.run(*(sys.argv[2:])))
