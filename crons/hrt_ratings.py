# coding=utf8
"""CHRT Ratings

Generates a CSV of customer who've reported on their HRT experience
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-01-22"

# Python imports
from base64 import b64encode
import csv
import io

# Pip imports
import arrow
from RestOC import Conf, Services

# Record imports
from records.monolith import TfAnswer, TfLanding

# Cron imports
from crons import isRunning, emailError

def run():
	"""Run

	Fetches CHRT with ratings and generates a list of the customer info

	Returns:
		bool
	"""

	# If it's already running, skip it
	if isRunning('hrt_ratings'):
		return True

	# Get all ratings in healthRatingCHRT, revitaExpectationsCHRT
	lAnswers = TfAnswer.filter({
		"questionId": ['healthRatingCHRT', 'revitaExpectationsCHRT']
	}, raw=['landing_id', 'questionId', 'value'])

	# Create a unique list of landing IDs
	dAnswers = {}
	for d in lAnswers:
		if d['landing_id'] not in dAnswers:
			dAnswers[d['landing_id']] = {}
		dAnswers[d['landing_id']][d['questionId']] = d['value']

	# Get the date and customer ID of all landings
	lLandings = TfLanding.filter({
		'landing_id': list(dAnswers.keys())
	}, raw=['landing_id', 'ktCustomerId', 'email', 'phone', 'firstName', 'lastName', 'createdAt'])

	# Create psuedo file
	oFile = io.StringIO()

	# Create a new CSV writer
	oCSV = csv.writer(oFile)

	# Add the header
	oCSV.writerow([
		'Customer ID','First Name','Last Name','Phone Number','E-mail Address',
		'Date Rated','Health Rating', 'Revita Expectations'
	])

	# Go through each landing
	for d in lLandings:

		# Write the line
		oCSV.writerow([
			d['ktCustomerId'],
			d['firstName'],
			d['lastName'],
			d['phone'],
			d['email'],
			d['createdAt'],
			dAnswers[d['landing_id']]['healthRatingCHRT'],
			dAnswers[d['landing_id']]['revitaExpectationsCHRT']
		])

	# Get the list of recipients for the report
	oResponse = Services.read('reports', 'recipients/internal', {
		"_internal_": Services.internalKey(),
		"name": 'HRT_Ratings'
	})
	if oResponse.errorExists():
		emailError('HRT Ratings Failed', 'Failed to get report recipients\n\n%s' % (
			str(oResponse)
		))
		return False

	# Store the recipients
	mRecipients = oResponse.data

	# Send the email
	oResponse = Services.create('communications', 'email', {
		"_internal_": Services.internalKey(),
		"text_body": 'This is an automated message, please do not respond',
		"subject": 'MaleExcel - HRT Ratings Report',
		"to": mRecipients,
		"attachments": {
			"body": b64encode(oFile.getvalue().encode("utf-8")).decode('utf-8'),
			"filename": 'hrt_ratings_%s.csv' % arrow.get().format('YYYY-MM-DD')
		}
	})
	if oResponse.errorExists():
		print(oResponse.error)

	# Return OK
	return True
