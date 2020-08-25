# coding=utf8
"""WelDyneRx Not Opened

Finds all triggers older than 72 hours that haven't been opened or shipped yet
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-23"

# Python imports
from base64 import b64encode
import csv
import io

# Pip imports
import arrow
from RestOC import Services

# Record imports
from records.welldyne import Trigger
from records.monolith import DsPatient

# Service imports
from services.konnektive import Konnektive

# Report imports
from reports import emailError, isRunning

def run(hours):
	"""Run

	Entry point into the script

	Arguments:
		hours (str): The age of the triggers in hours

	Returns:
		bool
	"""

	# Is the report already running
	if isRunning('welldyne_not_opened'):
		return True

	# Create a konnektive instance and initialise it
	oKNK = Konnektive()
	oKNK.initialise()

	# Init the list of lines for the report
	lLines = []

	# Convert the hours into a timestamp
	iAge = arrow.get().shift(hours=-(int(hours))).timestamp

	# Get all triggers with no error that haven't been opened/shipped
	lTriggers = Trigger.notOpened(iAge)

	# Go through each trigger found
	for d in lTriggers:

		print('Customer %s:%s' % (d['crm_type'], d['crm_id']))

		# Find the name of the customer in Konnektive via the order
		lOrders = oKNK._request('order/query', {
			"orderId": d['crm_order']
		})

		# Find the birthday in the DsPatient table
		dPatient = DsPatient.filter({"customerId": d['crm_id']}, raw=['dateOfBirth'], limit=1)

		# If there's no patient
		if not dPatient:
			continue

		# Add the line
		lLines.append([
			arrow.get(d['_created']).to('US/Eastern').format('YYYY-MM-DD HH:mm'),
			d['crm_id'].zfill(6),
			lOrders[0]['shipFirstName'],
			lOrders[0]['shipLastName'],
			dPatient['dateOfBirth'][0:10]
		])

	# Create a new temp file
	oFile = io.StringIO()

	# Create a new CSV writer
	oCSV = csv.writer(oFile)

	# Add the header
	oCSV.writerow([
		'Triggered','Member ID','First Name','Last Name','DOB'
	])

	# Write each record to the file
	for l in lLines:
		oCSV.writerow(l)

	# Set the file to the beginning
	oFile.flush()
	oFile.seek(0)

	# Get the list of recipients for the report
	oResponse = Services.read('reports', 'recipients/internal', {
		"_internal_": Services.internalKey(),
		"name": 'WellDyne_NotOpened'
	})
	if oResponse.errorExists():
		emailError('WellDyne Not Opened Failed', '%s\n\n%s' % (
			str(oResponse),
			oFile.getvalue()
		))
		return False

	# Send the email
	oResponse = Services.create('communications', 'email', {
		"_internal_": Services.internalKey(),
		"text_body": 'Triggered orders with no feedback in %s hours' % hours,
		"subject": 'No Feedback Report',
		"to": oResponse.data,
		"attachments": {
			"body": b64encode(oFile.getvalue().encode("utf-8")).decode('utf-8'),
			"filename": 'maleexcel_no_feedback_%s.csv' % arrow.get().format('YYYY-MM-DD')
		}
	})
	if oResponse.errorExists():
		emailError('WellDyne Not Opened Failed', '%s\n\n%s' % (
			str(oResponse),
			oFile.getvalue()
		))
		return False

	# Return A-OK
	return True
