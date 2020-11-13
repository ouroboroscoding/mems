# coding=utf8
""" Fake Message

Simulates a message coming in from Twilio
"""

# Python imports
import os, platform, sys

# Framework imports
from RestOC import Conf, Record_MySQL, REST, Services

# Services
from services import monolith

# Only run if called directly
if __name__ == "__main__":

	# Load the config
	Conf.load('config.json')
	sConfOverride = 'config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Add hosts
	Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))

	# Create the REST config instance
	oRestConf = REST.Config(Conf.get("rest"))

	# Register all services
	Services.register({}, oRestConf, Conf.get(('services', 'salt')))

	# Get an instance of the Monolith service and initialise it
	oMonolith = monolith.Monolith()
	oMonolith.initialise()

	# Create a new message using the passed data
	oMonolith.messageIncoming_create({
		"_internal_": Services.internalKey(),
		"customerPhone": sys.argv[1],
		"recvPhone": sys.argv[2],
		"content": sys.argv[3]
	})
