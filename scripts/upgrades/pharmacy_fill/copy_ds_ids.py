# coding=utf8
""" Copy the wd adhoc"""

# Pip imports
import arrow
from RestOC import Record_MySQL

# Service imports
from services.prescriptions.records import Medication, Pharmacy

def run():

	# Fetch all records in the monolith table
	lOld = Record_MySQL.Commands.select(
		'monolith',
		'SELECT * FROM `monolith`.`ds_product`',
		Record_MySQL.ESelect.ALL
	)

	# Go through each one and insert it into the new table
	for d in lOld:

		# Create the new instance
		oMedication = Medication({
			"_created": arrow.get(d['createdAt']).timestamp,
			"_updated": arrow.get(d['updatedAt']).timestamp,
			"name": d['name'],
			"dsIds": d['dsIds'],
			"synonyms": d['synonyms']
		})

		# Create the record
		oMedication.create(conflict='replace')

	# Fetch all records in the monolith table
	lOld = Record_MySQL.Commands.select(
		'monolith',
		'SELECT * FROM `monolith`.`ds_pharmacy`',
		Record_MySQL.ESelect.ALL
	)

	# Go through each one and insert it into the new table
	for d in lOld:

		# Create the new instance
		oPharmacy = Pharmacy({
			"_created": arrow.get(d['createdAt']).timestamp,
			"name": d['name'],
			"pharmacyId": d['pharmacyId']
		})

		# Create the record
		oPharmacy.create(conflict='replace')

	# Return OK
	return True
