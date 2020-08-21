# coding=utf8
""" Pharmacy Switch

Switches one pharmacy for another for every known customer
"""

# Python imports
import os, platform, sys

# Framework imports
from RestOC import Conf, Record_MySQL, REST, Services, Sesh

# Services
from services import prescriptions
from records.monolith import DsPatient

# Only run if called directly
if __name__ == "__main__":

	# Check arguments
	if len(sys.argv) != 3:
		print('This tool requires two arguments, the pharmacy ID to switch, and the pharmacy ID to switch to')
		sys.exit(1)

	# If we can't convert the arguments
	try:
		iFrom = int(sys.argv[1])
		iTo = int(sys.argv[2])
	except ValueError:
		print('Pharmacy IDs must be integers')
		sys.exit(1)

	# Load the config
	Conf.load('config.json')
	sConfOverride = 'config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Check if we have a file with the last ID processed
	sIDFile = '%s/pharmacy_switch.dat' % Conf.get('temp_folder', '/tmp')
	if os.path.exists(sIDFile):
		with open(sIDFile) as oF:
			iLastID = int(oF.read())
	else:
		iLastID = 0

	# Add hosts
	Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))

	# Create the REST config instance
	oRestConf = REST.Config(Conf.get("rest"))

	# Register all services
	Services.register({}, oRestConf, Conf.get(('services', 'salt')))

	# Init sessions and create one
	Sesh.init(Conf.get(("redis", "primary")))
	oSesh = Sesh.create()

	# Get an instance of the Prescriptions service and initialise it
	oPrescriptions = prescriptions.Prescriptions()
	oPrescriptions.initialise()

	# Fetch all Patient IDs
	lPatients = DsPatient.filter(
		{"patientId": {"neq": None}, "id": {"gt": iLastID}},
		raw=['id', 'patientId'],
		orderby=['id']
	)

	# Go through each one
	for dP in lPatients:

		# Convert the ID
		iID = int(dP['patientId'])

		# Get the pharmacies using the patient ID
		oResponse = oPrescriptions.patientPharmacies_read({"patient_id": iID}, oSesh)
		if oResponse.errorExists():
			print(oResponse.error)
			sys.exit(1);

		# Go through each pharmacy
		for dPharmacy in oResponse.data:

			# If we find one with the ID to switch out
			if dPharmacy['PharmacyId'] == iFrom:

				print('--------------------------------------')
				print('%d had %d' % (iID, iFrom))

				# Add the new pharmacy
				oResponse = oPrescriptions.patientPharmacy_create({"patient_id": iID, "pharmacy_id": iTo}, oSesh)
				if oResponse.errorExists():
					print(oResponse.error)
					sys.exit(1);

				# Delete the old pharmacy
				oResponse = oPrescriptions.patientPharmacy_delete({"patient_id": iID, "pharmacy_id": iFrom}, oSesh)
				if oResponse.errorExists():
					print(oResponse.error)
					sys.exit(1);

				# Stop the loop
				break

		# Set the last ID
		iLastID = dP['id']
		with open(sIDFile, 'w') as oF:
			oF.write('%d' % iLastID)
