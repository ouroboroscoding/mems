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

# Record imports
from records.welldyne import AdHoc, Eligibility

# Service imports
from services.konnektive import Konnektive

# Cron imports
from crons import emailError, isRunning

def run(period=None):
	"""Run

	Fetches all the adhoc records and generates and uploads the report for
	WellDyne

	Arguments:
		period (str): The time period of the day to generate the files for

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('wd_adhoc'):
		return True

	try:

		# Init the Konnektive service
		oKnk = Konnektive()
		oKnk.initialise()

		# Create a list of data that will be added to the file
		lLines = []

		# Generate the since and thru dates for potential eligibility updates
		sSince = arrow.get().format('YYYY-MM-DD 00:00:00')
		sThru = arrow.get().shift(days=15).format('YYYY-MM-DD 00:00:00')

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
		lAdHocs = AdHoc.report()

		# Go through each one
		for d in lAdHocs:

			# Split the raw data by comma
			lLine = d['raw'].split(',')

			# Replace the first element
			lLine[0] = d['type']

			# If the type is extend eligibility
			if d['type'] == 'Extend Eligibility':

				# Generate timestamp
				sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

				# Create or update the eligibility
				oElig = Eligibility({
					"customerId": d['crm_id'],
					"memberSince": sSince,
					"memberThru": sThru,
					"createdAt": sDT,
					"updatedAt": sDT
				})
				oElig.create(conflict=('memberThru', 'updatedAt'))

			# Else, if the type is update address
			elif d['type'] == 'Update Address':

				# Find the order
				lOrders = oKnk._request('order/query', {
					"orderId": d['crm_order']
				})

				# Update the appropriate fields
				lLine[3] = lOrders[0]['shipFirstName'] or ''
				lLine[4] = lOrders[0]['shipLastName'] or ''
				lLine[6] = lOrders[0]['shipAddress1'] or ''
				lLine[7] = lOrders[0]['shipAddress1'] or ''
				lLine[8] = lOrders[0]['shipCity'] or ''
				lLine[9] = lOrders[0]['shipState'] or ''
				lLine[10] = lOrders[0]['shipPostalCode'] or ''

			# Add the data to the lines
			lLines.append(lLine)

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
		for l in lLines:
			oCSV.writerow(l)

		# Set the file to the beginning
		oFile.flush()
		oFile.seek(0)

		# Generate the filename with the current date
		sDate = '%s%s' % (arrow.get().format('YYYYMMDD'), sFileTime)
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

		# Delete the adhocs processed
		#Adhoc.deleteGet([
		#	d['_id'] for d in lAdHocs
		#])

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
