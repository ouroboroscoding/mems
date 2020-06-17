# coding=utf8
""" Triggers

Goes through old trigger files and
"""

# Python imports
import csv, os, platform, sys

# Framework imports
from RestOC import Conf, Record_MySQL, REST, Services, Sesh

# Services
from services.monolith.records import WdTrigger

# Only run if called directly
if __name__ == "__main__":

	# Load the config
	Conf.load('../config.json')
	sConfOverride = '../config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Add hosts
	Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))

	# Create an object to go through every existing trigger file
	dTriggers = {
		"TRIGGER20200617130000.TXT": {"type": None, "date": '2020-06-16 13:00:00'}
	}

	# Go through each file
	for sFile in dTriggers:

		# Open the file
		with open('../Triggers/%s' % sFile) as oF:

			print(sFile)

			# Get a csv iterator
			it = csv.reader(oF, delimiter=',', quotechar='"')

			# Go through each line
			for lLine in it:

				# If the line is Type or Medication
				if lLine[0] in ['Type', 'Medication (Name + Strength)']:
					continue

				# Init the record structure
				dRecord = {
					"customerId": None,
					"type": dTriggers[sFile]['type'],
					"triggered": dTriggers[sFile]['date'],
					"opened": None,
					"shipped": None
				}

				# If we have a type
				if dRecord['type']:
					dRecord['customerId'] = lLine[10].lstrip('0')
				else:
					dRecord['type'] = lLine[0]
					dRecord['customerId'] = lLine[11].lstrip('0')

				print(dRecord)

				# Create an instance of the record
				try:
					oTrigger = WdTrigger(dRecord);
				except ValueError as e:
					print(e)
					print(dRecord)
					sys.exit(1)

				# Add the record to the DB
				oTrigger.create(conflict='replace')
