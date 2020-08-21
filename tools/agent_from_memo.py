# coding=utf8
"""Agent From Memo

Creates an agent user from an existing memo account
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-14"

# Python imports
import os
import platform
import sys

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL, REST, Services, Sesh

# Record imports
from records.monolith import User

# Service imports
from services.csr import CSR

# If the version argument is missing
if len(sys.argv) < 2:
	print('Must specify a username\n\tpython -m tools.agent_from_memo bast')
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

# Init the Sesh module
Sesh.init(Conf.get(("redis", "primary")))

# Register all services
Services.register({
		'auth':None,
		'monolith':None
	},
	REST.Config(Conf.get("rest")),
	Conf.get(('services', 'salt'))
)

# Find the memo user
dUser = User.filter(
	{"userName": sys.argv[1]},
	raw=['id'],
	limit=1
)

# If there's no user
if not dUser:
	print('No user found for "%s"' % sys.argv[1])
	sys.exit(1)

# Create a new session
oSesh = Sesh.create()
oSesh['user_id'] = 0
oSesh.save()

# Init the CSR instance
oCSR = CSR()
oCSR.initialise()

# Create the agent
oResponse = oCSR._agent_create(dUser['id'], oSesh)

# Delete the session
oSesh.close

# If there's an error
if oResponse.errorExists():

	# If it's a duplicate
	if oResponse.error['code'] == 1101:
		print('Memo user already an Agent')
	else:
		print('Unknown error: %s' % str(oResponse.error))

	# Error exit
	sys.exit(1)

# Succes message with agent ID
print('Success: %s' % oResponse.data)
sys.exit(0)
