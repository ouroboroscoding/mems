# coding=utf8
"""AdHoc

Generates the WellDyne adhoc report
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-03"

# Python imports
import csv
import io
import traceback

# Pip imports
import arrow
import pysftp
from RestOC import Conf, DictHelper

# Service imports
from records.prescriptions import PharmacyFillError
from records.welldyne import AdHoc, RxNumber

# Cron imports
from crons import isRunning
from crons.shared import Allergies, PharmacyFill

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

		# Try to find the customer's RX number
		dRx = RxNumber.filter({
			"member_id": sMemberID
		}, raw=['number'], limit=1)

		# If it exists
		if dRx:
			data['rx'] = dRx['number']

		# Generate timestamp
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Create the CSV line
		lLine = [
			data['type'],
			data['medication'],
			data['rx'],
			data['first'],
			data['last'],
			data['dob'],
			data['address1'],
			data['address2'] or '',
			data['city'],
			data['state'],
			data['postalCode'],
			sMemberID,
			Allergies.fetch(data)
		];

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
		sFilename = 'ADHOC%s.CSV' % sDate;

		# Get the sFTP config
		dSFTP = DictHelper.clone(Conf.get(('welldyne', 'sftp')))

		# Pull off the subdirectory if there is one
		sFolder = dSFTP.pop('folder', None)
		if sFolder:
			sFilename = '%s/%s' % (sFolder, sFilename)

		# Upload the file to the sFTP
		with pysftp.Connection(**dSFTP) as oCon:
			oCon.putfo(oFile, sFilename, confirm=False)

def run(period=None):
	"""Run

	Fetches all the adhoc records and generates and uploads the report for
	WellDyne

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	try:

		# Init the PharmacyFill module
		PharmacyFill.initialise()

		# Create a new instance of the WellDyne Trigger File
		oTrigger = TriggerFile()

		# If we're doing the noon run
		if period == 'noon':
			sFileTime = '120000'

		# Else, if we're doing the mid day run
		elif period == 'afternoon':
			sFileTime = '160000'

		# Else, invalid time period
		else:
			print('Invalid time period: %s' % time)
			return False

		# Find all AdHoc records
		lAdHocs = AdHoc.get()

		# Go through each one
		for o in lAdHocs:

			print('\tWorking on %s...' % o['crm_id'])

			# Try to process it
			dRes = PharmacyFill.process({
				"crm_type": o['crm_type'],
				"crm_id": o['crm_id'],
				"crm_order": o['crm_order']
			})

			# If we get success
			if dRes['status']:

				# Go through each medication returned
				for dData in dRes['data']:

					# Overwrite the type
					dData['type'] = o['type']

					# If the pharmacy is Castia/WellDyne
					if dData['pharmacy'] in ['Castia', 'WellDyne']:

						# Add it to the Trigger
						oTrigger.add(dData)

					else:
						emailError('NON-WELLDYNE ADHOC', str(o.record()))
						continue

				# Move it to the sent table
				o.sent()

		# Fetch all previous adhoc error records that are ready to be re-processed
		lFillErrors = PharmacyFillError.filter({
			"list": 'adhoc',
			"ready": True
		})

		# Go through each record
		for o in lFillErrors:

			# Try to process it
			dRes = PharmacyFill.process({
				"crm_type": o['crm_type'],
				"crm_id": o['crm_id'],
				"crm_order": d['crm_order']
			})

			# If we get success
			if dRes['status']:

				# Go through each medication returned
				for dData in dRes['data']:

					# Overwrite the type
					dData['type'] = o['type']

					# If the pharmacy is Castia/WellDyne
					if dData['pharmacy'] not in ['Castia', 'WellDyne']:
						emailError('WELLDYNE PHARMACY SWITCH', str(o.record()))
						continue

					# Add it to the Trigger
					oTrigger.add(dData)

					# Add it to the adhoc sent
					AdHocSent.fromFillError(o)

				# Delete it
				o.delete()

			# Else, if it failed to process again
			else:

				# Increment the fail count, overwrite the reason, and reset the
				#	ready flag
				o['fail_count'] += 1
				o['reason'] = dRes['data']
				o['ready'] = False
				o.save();

		# Upload the WellDyne trigger file
		oTrigger.upload(sFileTime)

		# Return OK
		return True

	# Catch any error and email it
	except Exception as e:
		sBody = '%s\n\n%s' % (
			', '.join([str(s) for s in e.args]),
			traceback.format_exc()
		)
		emailError('AdHoc Failed', sBody)
		return False
