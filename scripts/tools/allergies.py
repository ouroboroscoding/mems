# coding=utf8
""" Allergies

Fetches the allergies associated with a specific customer
"""

# Python imports
import os, platform, sys

# Framework imports
from RestOC import Conf, Record_MySQL, REST, Services, Sesh

# Services
from services import monolith
from services.monolith.records import KtCustomer, TfLanding, TfAnswer

# Only run if called directly
if __name__ == "__main__":

	# Load the config
	Conf.load('../config.json')
	sConfOverride = '../config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Add hosts
	Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))

	# Create the REST config instance
	oRestConf = REST.Config(Conf.get("rest"))

	# Register all services
	Services.register({}, oRestConf, Conf.get(('services', 'salt')))

	# Init sessions and create one
	Sesh.init(Conf.get(("redis", "primary")))
	oSesh = Sesh.create()

	# Get an instance of the Monolith service and initialise it
	oMonolith = monolith.Monolith()
	oMonolith.initialise()

	print('Customer ID: %s' % sys.argv[1])

	# Get the last name, email address, and phone number of the customer
	dCustomer = KtCustomer.filter(
		{"customerId": sys.argv[1]},
		raw=['lastName', 'emailAddress', 'phoneNumber'],
		limit=1
	)

	# Try to find the landings
	lLandings = TfLanding.find(
		dCustomer['lastName'],
		dCustomer['emailAddress'] or '',
		dCustomer['phoneNumber'] or ''
	)
	if lLandings:
		lLandings = [d['landing_id'] for d in lLandings]

	print('Landing IDs: %s' % ', '.join(lLandings))

	# Try to find allergy answers in the landings
	if lLandings:
		lAnswers = TfAnswer.filter({
			"landing_id": lLandings,
			"ref": ['95f9516a-4670-43b1-9b33-4cf822dc5917', 'allergies']
		}, raw=['answer'])
		if lAnswers:
			lAnswers = [d['answer'] for d in lAnswers]

	print('Answers: %s' % ', '.join(lAnswers))
