# coding=utf8
""" Fake Message

Simulates a message coming in from Twilio
"""

# Python imports
import os, platform, sys

# Framework imports
from RestOC import Conf, Record_MySQL, REST, Services

# Services
from services import monolith, dosespot

# Load the config
Conf.load('../config.json')
sConfOverride = '../config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add hosts
Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))
Record_MySQL.addHost('monolith_prod', Conf.get(("mysql", "hosts", "monolith_prod")))

# Create the REST config instance
oRestConf = REST.Config(Conf.get("rest"))

# Register all services
Services.register({}, oRestConf, Conf.get(('services', 'salt')))

# Get an instance of the Monolith service and initialise it
oMonolith = monolith.Monolith()
oMonolith.initialise()

print(sys.argv[1])

# Get the patient ID from the customer ID
oEff = oMonolith.customerDsid_read({"customerId": sys.argv[1]}, {})
if oEff.errorExists():
	print(oEff.error)
	sys.exit(1);

# If we don't have the patient ID
if not oEff.data:
	print('No patient ID found');
	sys.exit(0);

# Get an instance of the Dosespot service and initialise it
oDosespot = dosespot.Dosespot()
oDosespot.initialise()

# Get the prescriptions using the patient ID
oEff = oDosespot.patientPrescriptions_read({"patient_id": int(oEff.data)})
if oEff.errorExists():
	print(oEff.error)
	sys.exit(1);

# Print the prescriptions
print(oEff.data);
