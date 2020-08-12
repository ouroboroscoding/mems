# coding=utf8
"""Generic

Class to generate a CSV file and email it
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-03"

# Python imports
from base64 import b64encode
import csv
import io

# Pip imports
import arrow
from RestOC import Services

# Service imports
from records.prescriptions import Pharmacy

class EmailFile(object):
	"""Email File

	Handles generating a file to email
	"""

	def __init__(self):
		"""Constructor

		Initialises the instance

		Arguments:
			file_time (str): The time to append to the report name

		Returns:
			EmailFile
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

		# Add the data as a new line
		self.lines.append([
			data['first'],
			data['last'],
			data['address1'],
			data['address2'],
			data['city'],
			data['state'],
			data['country'],
			data['postalCode'],
			data['email'],
			data['phone'],
			data['dob'],
			data['medication']
		]);

	def send(self, pharmacy, file_time):
		"""Send

		Generates the csv file and emails it to the appropriate people

		Arguments:
			pharmacy (str): The name of the pharmacy
			file_time (str): The time to append to the report name

		Returns:
			None
		"""

		# Look up the addresses to email this report to
		dPharmacy = Pharmacy.filter({
			"name": pharmacy
		}, raw=['reports_to'], limit=1)

		# If we got nothing, do nothing
		if not dPharmacy:
			return

		# Split the emails by comma
		lTo = dPharmacy['reports_to'].split(',')

		# If we have none, do nothing
		if not lTo:
			return

		# Create psuedo file
		oFile = io.StringIO()

		# Create a new CSV writer
		oCSV = csv.writer(oFile)

		# Add the header
		oCSV.writerow([
			'First Name','Last Name','Address 1','Address 2','City','State',
			'Country','Zip','Email','Phone','DOB','Product'
		])

		# Write each record to the file
		for l in self.lines:
			oCSV.writerow(l)

		# Send the email
		oEff = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"text_body": 'This is an automated message, please do not respond',
			"subject": 'MaleExcel - %s Refill Report' % pharmacy,
			"to": lTo,
			"attachments": {
				"body": b64encode(oFile.getvalue().encode("utf-8")).decode('utf-8'),
				"filename": 'refill_report_%s_%s.csv' % (
					arrow.get().format('YYYY-MM-DD'),
					file_time
				)
			}
		})
		if oEff.errorExists():
			print(oEff.error)
