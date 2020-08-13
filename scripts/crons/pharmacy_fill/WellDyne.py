# coding=utf8
"""WellDyne Pharmacy Fill

Class to generate a trigger file and upload it to WellDyne sFTP
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-02"

# Python imports
import csv
import io

# Pip imports
import arrow
import pysftp
from RestOC import Conf, DictHelper

# Service imports
from services.welldyne.records import Eligibility, RxNumber, Trigger

# Local imports
from crons.shared import Allergies

class TriggerFile(object):
	"""Trigger File

	Handles generating a file to upload to WellDyne's sFTP
	"""

	def __init__(self):
		"""Constructor

		Initialises the instance

		Arguments:
			period (str): The time period of the day to generate the files for

		Returns:
			TriggerFile
		"""

		# Init the lines for the file
		self.lines = []

		# Generate the since and thru dates
		self.since = arrow.get().format('YYYY-MM-DD 00:00:00')
		self.thru = arrow.get().shift(days=15).format('YYYY-MM-DD 00:00:00')

	def add(self, data):
		"""Add

		Adds a line to the report

		Arguments:
			data (dict): The data needed to make the line

		Returns:
			None
		"""

		# Zero fill the member ID
		sMemberID = data['crm_id'].zfill(6)

		# See if we have a previous trigger for this customer and medication
		dLastTrigger = Trigger.filter({
			"crm_type": data['crm_type'],
			"crm_id": data['crm_id'],
			"crm_order": {"neq": data['crm_order']},
			"medication": data['medication']
		}, raw=['rx_id'], orderby=[('_created', 'DESC')], limit=1)

		# If it's an initial
		if data['type'] == 'initial':

			# If we have one, and the rx_id matches the ds_id, it's a new order
			#	but not a new prescription
			if dLastTrigger and dLastTrigger['rx_id'] == str(data['ds_id']):

				# Overwrite the type
				data['type'] = 'refill'

		# If the type is refill
		if data['type'] == 'refill':

			# If we have one, and the rx_id does not matches the ds_id, it's
			#	a recurring order, but the prescription has changed
			if dLastTrigger and dLastTrigger['rx_id'] != str(data['ds_id']):

				# Overwrite the type
				data['type'] = 'initial'

			# Else, a legitimate refill
			else:

				# Try to find the customer's RX number
				dRx = RxNumber.filter({
					"member_id": sMemberID
				}, raw=['number'], limit=1)

				# If it exists, add it to the trigger
				if dRx:
					data['rx'] = dRx['number']

		# Generate timestamp
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Create or update the eligibility
		oElig = Eligibility({
			"customerId": data['crm_id'],
			"memberSince": self.since,
			"memberThru": self.thru,
			"createdAt": sDT,
			"updatedAt": sDT
		})
		oElig.create(conflict=('memberThru', 'updatedAt'))

		# Create the CSV line
		lLine = [
			data['type'] or '',
			data['medication'] or '',
			str(data['rx']) or '',
			data['first'] or '',
			data['last'] or '',
			data['dob'] or '',
			data['address1'] or '',
			data['address2'] or '',
			data['city'] or '',
			data['state'] or '',
			data['postalCode'],
			sMemberID,
			Allergies.fetch(data)
		];

		# Create a trigger instance
		oTrigger = Trigger({
			"crm_type": data['crm_type'],
			"crm_id": data['crm_id'],
			"crm_order": data['crm_order'],
			"medication": data['medication'],
			"rx_id": str(data['ds_id']),
			"type": data['type'],
			"raw": ','.join(lLine)
		})

		# Create the record in the DB
		oTrigger.create(conflict='replace')

		# Add the line to the report
		self.lines.append(lLine);

	def upload(self, file_time):
		"""Upload

		Takes the lines added by the add method and generates the full report
		then uploads it to the sFTP

		Arguments:
			file_time (str): The time to add to the end of the file name

		Returns:
			None
		"""

		# Create a new temp file
		oFile = io.StringIO()

		# Create a new CSV writer
		oCSV = csv.writer(oFile)

		# Add the header
		oCSV.writerow([
			'Type',
			'Medication (Name + Strength)','Prescription Number','Patient First Name',
			'Patient Last Name','Patient Date of Birth','Address','Address #2',
			'City','State','Patient Zip Code','Member ID Number','Allergies'
		])

		# Write each record to the file
		for l in self.lines:
			oCSV.writerow(l)

		# Set the file to the beginning
		oFile.flush()
		oFile.seek(0)

		# Generate the filename with the current date
		sDate = '%s%s' % (arrow.get().format('YYYYMMDD'), file_time)
		sFilename = 'TRIGGER%s.TXT' % sDate;

		# Get the sFTP config
		dSFTP = DictHelper.clone(Conf.get(('welldyne', 'sftp')))

		# Pull off the subdirectory if there is one
		sFolder = dSFTP.pop('folder', None)
		if sFolder:
			sFilename = '%s/%s' % (sFolder, sFilename)

		# Upload the file to the sFTP
		with pysftp.Connection(**dSFTP) as oCon:
			oCon.putfo(oFile, sFilename, confirm=False)

def dateDigits(date):
	"""Date Digits

	Returns just the digits of a date

	Arguments:
		date (str): The date as a string

	Returns:
		str
	"""
	return '%s%s%s' % (date[0:4], date[5:7], date[8:10])

def eligibilityUpload(file_time):
	"""Eligibility Upload

	Fetches the valid eligibility, generates a report, and uploads it to
	the sFTP for WellDyne to consume

	Arguments:
		file_time (str): The time to append to the name of the uploaded file

	Returns:
		None
	"""

	# Find all records that have a member through date
	print('Fetching eligible members')
	lRecords = Eligibility.withCustomerData()

	# Init the list of lines
	lLines = []

	# Go through each record and generate the line
	print('Generating eligibility file')
	for d in lRecords:
		lLines.append(''.join([
			'ED'.ljust(15),										# Group ID
			str(d['customerId']).zfill(6).ljust(18),			# Member ID
			'00',												# Person code
			'1',												# Relationship
			(d['shipLastName'] or '')[0:25].ljust(25),			# Last Name
			(d['shipFirstName'] or '')[0:15].ljust(15),			# First Name
			' ',												# Middle initial
			'M',												# Sex
			dateDigits(d['dob'] or '').ljust(8),			# DOB
			' ',												# Multiple Birth Code
			'                  ',								# DurKey
			'         ',										# Unique ID for Accums
			(d['shipAddress1'] or '')[0:40].ljust(40),			# Address 1
			(d['shipAddress2'] or '')[0:40].ljust(40),			# Address 2
			'                                        ',			# Address 3
			(d['shipCity'] or '')[0:20].ljust(20),				# City
			(d['shipState'] or '')[0:2].ljust(2),				# State
			(d['shipPostalCode'] or '')[0:5].ljust(5),			# Zip 5
			'    ',												# Zip 5 + 4
			'  ',												# Zip 5 + 4 + 2
			(d['phoneNumber'] or '')[-10:].ljust(10),			# Phone
			' ',												# Family Flag
			' ',												# Family Type
			'                  ',								# Family ID
			'        ',											# Benefit Reset Date
			dateDigits(d['memberSince']).ljust(8),		# Member From Date
			dateDigits(d['memberThru']).ljust(8),			# Member Thru Date
			'               ',									# PCP ID
			'  ',												# PCP ID Qualifier
			'  ',												# PCP ID State
			' ',												# Alt Ins Flag
			'          ',										# Alt Ins Code
			'        ',											# Alt Ins From Date
			'        ',											# Alt Ins Thru Date
			'                  ',								# Unique Patient ID
			'                    ',								# Diagnosis Code 1
			'        ',											# Diagnosis Code 1 From Date
			'        ',											# Diagnosis Code 1 Thru Date
			'  ',												# Qualifier 1
			'                    ',								# Diagnosis Code 2
			'        ',											# Diagnosis Code 2 From Date
			'        ',											# Diagnosis Code 2 Thru Date
			'  ',												# Qualifier 2
			'                    ',								# Diagnosis Code 3
			'        ',											# Diagnosis Code 3 From Date
			'        ',											# Diagnosis Code 3 Thru Date
			'  ',												# Qualifier 3
			(d['emailAddress'] or '')[0:50].ljust(50),			# E-mail address
			'           '										# ID Card Template
	]))

	# Generate the filename with the current date
	sDate = '%s%s' % (arrow.get().format('YYYYMMDD'), file_time)
	sFilename = 'RWTMEXCEL%s.TXT' % sDate;

	# Get the sFTP config
	dSFTP = DictHelper.clone(Conf.get(('welldyne', 'sftp')))

	# Pull off the subdirectory if there is one
	sFolder = dSFTP.pop('folder', None)
	if sFolder:
		sFilename = '%s/%s' % (sFolder, sFilename)

	# Upload the file to the sFTP
	print('Connecting to sFTP')
	with pysftp.Connection(**dSFTP) as oCon:
		print('Uploading file: %s' % sFilename)
		oCon.putfo(io.StringIO('\n'.join(lLines)), sFilename, confirm=False)
