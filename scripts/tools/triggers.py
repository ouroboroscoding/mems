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
		"INITIALS20200529.TXT": {"type": 'initials', "date": '2020-05-29 04:30:00'},
		"REFILLS20200529.TXT": {"type": 'refills', "date": '2020-05-29 04:30:00'},
		"INITIALS20200530.TXT": {"type": 'initials', "date": '2020-05-30 04:30:00'},
		"REFILLS20200530.TXT": {"type": 'refills', "date": '2020-05-30 04:30:00'},
		"INITIALS20200531.TXT": {"type": 'initials', "date": '2020-05-31 04:30:00'},
		"REFILLS20200531.TXT": {"type": 'refills', "date": '2020-05-31 04:30:00'},
		"INITIALS20200601.TXT": {"type": 'initials', "date": '2020-06-01 04:30:00'},
		"REFILLS20200601.TXT": {"type": 'refills', "date": '2020-06-01 04:30:00'},
		"INITIALS20200602.TXT": {"type": 'initials', "date": '2020-06-02 04:30:00'},
		"REFILLS20200602.TXT": {"type": 'refills', "date": '2020-06-02 04:30:00'},
		"INITIALS20200603.TXT": {"type": 'initials', "date": '2020-06-03 04:30:00'},
		"REFILLS20200603.TXT": {"type": 'refills', "date": '2020-06-03 04:30:00'},
		"INITIALS20200604.TXT": {"type": 'initials', "date": '2020-06-04 04:30:00'},
		"REFILLS20200604.TXT": {"type": 'refills', "date": '2020-06-04 04:30:00'},
		"INITIALS20200605.TXT": {"type": 'initials', "date": '2020-06-05 04:30:00'},
		"REFILLS20200605.TXT": {"type": 'refills', "date": '2020-06-05 04:30:00'},
		"TRIGGER20200606043000.TXT": {"type": None, "date": '2020-06-06 04:30:00'},
		"TRIGGER20200606130000.TXT": {"type": None, "date": '2020-06-06 13:00:00'},
		"TRIGGER20200607043000.TXT": {"type": None, "date": '2020-06-07 04:30:00'},
		"TRIGGER20200607130000.TXT": {"type": None, "date": '2020-06-07 13:00:00'},
		"TRIGGER20200608043000.TXT": {"type": None, "date": '2020-06-08 04:30:00'},
		"TRIGGER20200608130000.TXT": {"type": None, "date": '2020-06-08 13:00:00'},
		"TRIGGER20200609043000.TXT": {"type": None, "date": '2020-06-09 04:30:00'},
		"TRIGGER20200609130000.TXT": {"type": None, "date": '2020-06-09 13:00:00'},
		"TRIGGER20200610043000.TXT": {"type": None, "date": '2020-06-10 04:30:00'},
		"TRIGGER20200610130000.TXT": {"type": None, "date": '2020-06-10 13:00:00'},
		"TRIGGER20200611043000.TXT": {"type": None, "date": '2020-06-11 04:30:00'},
		"TRIGGER20200611130000.TXT": {"type": None, "date": '2020-06-11 13:00:00'},
		"TRIGGER20200612043000.TXT": {"type": None, "date": '2020-06-12 04:30:00'},
		"TRIGGER20200612130000.TXT": {"type": None, "date": '2020-06-12 13:00:00'},
		"TRIGGER20200613043000.TXT": {"type": None, "date": '2020-06-13 04:30:00'},
		"TRIGGER20200613130000.TXT": {"type": None, "date": '2020-06-13 13:00:00'},
		"TRIGGER20200614043000.TXT": {"type": None, "date": '2020-06-14 04:30:00'},
		"TRIGGER20200614130000.TXT": {"type": None, "date": '2020-06-14 13:00:00'},
		"TRIGGER20200615043000.TXT": {"type": None, "date": '2020-06-15 04:30:00'},
		"TRIGGER20200615130000.TXT": {"type": None, "date": '2020-06-15 13:00:00'},
		"TRIGGER20200616043000.TXT": {"type": None, "date": '2020-06-16 04:30:00'},
		"TRIGGER20200616130000.TXT": {"type": None, "date": '2020-06-16 13:00:00'}
	}

	# Go through each file
	for sFile in dTriggers:

		# Open the file
		with open('../Triggers/%s' % sFile) as oF:

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

				# Create an instance of the record
				try:
					oTrigger = WdTrigger(dRecord);
				except ValueError as e:
					print(e)

				# Add the record to the DB
				oTrigger.create(conflict='replace')
