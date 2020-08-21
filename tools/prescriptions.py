# coding=utf8
""" Prescriptions

Fetches the prescriptions associated with a specific customer
"""

# Python imports
import os, platform, pprint, sys

# Framework imports
from RestOC import Conf, Record_MySQL, REST, Services, Sesh

# Services
from records.monolith import DsPatient
from services import prescriptions

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
	Services.register({"auth":None}, oRestConf, Conf.get(('services', 'salt')))

	print('Customer ID: %s' % sys.argv[1])

	# Get the patient ID from the customer ID
	dPatient = DsPatient.filter({"customerId": sys.argv[1]}, raw=['patientId'], limit=1)

	# If we don't have the patient ID
	if not dPatient:
		print('No patient ID found');
		sys.exit(0);

	print('Patient ID: %s' % dPatient['patientId'])

	# Get an instance of the Prescriptions service and initialise it
	oPrescriptions = prescriptions.Prescriptions()
	oPrescriptions.initialise()

	# Get the prescriptions using the patient ID
	oResponse = oPrescriptions.patientPrescriptions_read({
		"_internal_": Services.internalKey(),
		"patient_id": int(dPatient['patientId'])
	})
	if oResponse.errorExists():
		print(oResponse.error)
		sys.exit(1);

	# Print the prescriptions
	print('Prescriptions: ')
	pprint.pprint(oResponse.data);
