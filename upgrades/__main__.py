# coding=utf8
""" Upgrades Entry

Handles running upgrade scripts
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-03-29"

# Python imports
import importlib
import os
import platform
import sys

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL, REST, Services

# Upgrade imports
from . import UpgradeLog, run

# If the version argument is missing
if len(sys.argv) < 2:
	print('Must specify the version to run:\n\tpython -m upgrades v1.0')
	sys.exit(1)

# Store the version
sVer = sys.argv[1].replace('.', '_')
sVer = sVer.replace('/', '.')

# Load the config
Conf.load('config.json')
sConfOverride = 'config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add the global prepend, monolith host, and primary host to mysql
Record_Base.dbPrepend(Conf.get(("mysql", "prepend"), ''))
Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))
Record_MySQL.addHost('primary', Conf.get(("mysql", "hosts", "primary")))

# Register all services
Services.register(
	{k:None for k in Conf.get(('rest', 'services'))},
	REST.Config(Conf.get("rest")),
	Conf.get(('services', 'salt'))
)

# Try to import the version
try:
	oVer = importlib.import_module('upgrades.%s' % sVer)
except ImportError as e:
	print('The given version "%s" is invalid.' % sVer)
	print(e)
	sys.exit(1)

# Load or create the version file
oLogFile = UpgradeLog('upgrades/%s/_upgrade.log' % sVer)

# Run the version files
run(oVer.modules, oLogFile)
