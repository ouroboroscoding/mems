# coding=utf8
"""WellDyneRX Reports

Generates and emails WellDyne reports
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-07-16"

# Python imports
from base64 import b64encode
import csv
import io

# Pip imports
import arrow
from RestOC import Conf, Record_MySQL, Services

# Cron imports
from crons import isRunning

def no_feedback(hours):
	"""No Feedback

	Checks on triggered orders that have no error or shipping in X number of
	hours

	Arguments:
		hours (uint): The number of hours to check by

	Returns:
		bool
	"""

	# If the script already running?
	if isRunning('wd_trigger_no_feedback'):
		return True

	# Generate SQL
	sSQL = 'SELECT ' \
				'`wdt`.`customerId`, ' \
				'`wdt`.`type`, ' \
				'`wdt`.`triggered`, ' \
				'`ktc`.`firstName`, ' \
				'`ktc`.`lastName` ' \
			'FROM `monolith`.`wd_trigger` as `wdt` ' \
			'LEFT JOIN `monolith`.`wd_outreach` as `wdo` ON `wdt`.`customerId` = `wdo`.`customerId` ' \
			'LEFT JOIN `monolith`.`kt_customer` as `ktc` ON `wdt`.`customerId` = `ktc`.`customerId` ' \
			'WHERE `wdt`.`opened` IS NULL ' \
			'AND `wdt`.`shipped` IS NULL ' \
			'AND `wdo`.`customerId` IS NULL ' \
			'AND `wdt`.`triggered` < DATE(NOW() - INTERVAL %d HOUR) ' \
			'ORDER BY `wdt`.`triggered` ASC ' % hours

	# Fetch the data from SQL
	lRecords = Record_MySQL.Commands.select('monolith', sSQL)

	# Generate a string file
	oFile = io.StringIO()

	# Create a new CSV writer
	oCSV = csv.writer(oFile)

	# Add the header
	oCSV.writerow(['CustomerID', 'Type', 'Triggered', 'First Name', 'Last Name'])

	# Write each record to the file
	for d in lRecords:
		oCSV.writerow([d['customerId'], d['type'], d['triggered'], d['firstName'], d['lastName']])

	# Send the email
	oEff = Services.create('communications', 'email', {
		"_internal_": Services.internalKey(),
		"text_body": 'Triggered orders with no feedback in %d hours' % hours,
		"subject": 'No Feedback Report',
		"to": Conf.get(('crons', 'welldyne', 'reports')),
		"attachments": {
			"body": b64encode(oFile.getvalue().encode("utf-8")).decode('utf-8'),
			"filename": 'maleexcel_no_feedback_%s.csv' % arrow.get().format('YYYY-MM-DD')
		}
	})
	if oEff.errorExists():
		print(oEff)
		return False

	# A-OK
	return True

def run(type, arg1=None):
	"""Run

	Entry point into the script

	Arguments:
		type (str): The type of report to generate
		arg1 (str): Possible data passed to the report

	Returns:
		bool
	"""

	# Trigger No Feedback report
	if type == 'no_feedback':

		# If no hours sent, assume 72
		if not arg1:
			arg1 = 72

		# Call the report
		return no_feedback(int(arg1))

	# Got an invalid report
	print('Invalid report type: %s' % type)
	return False
