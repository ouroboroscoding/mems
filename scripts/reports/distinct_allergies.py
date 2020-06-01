# coding=utf8
"""Distinct Allergies

Fetches all allergy answers from MIP and returns distinct counts
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-19"

# Python imports
import os
import platform

# Pip imports
from RestOC import Record_MySQL

# Shared imports
from shared import JSON

# Defines
LANDING_SQL = "SELECT `landing_id` " \
				"FROM `monolith`.`tf_landing` " \
				"WHERE `complete` = 'Y'"
VALUE_SQL = 'SELECT `landing_id`, `value` ' \
				'FROM `monolith`.`tf_answer` ' \
				'WHERE `landing_id` IN ("%s") ' \
				'AND `ref` IN ("95f9516a-4670-43b1-9b33-4cf822dc5917", "allergies")'

def run():
	"""Run

	Primary entry point of the report

	Returns:
		int
	"""

	# Distinct values
	dDistinct = {
		'': 0,
		'none': 0
	}

	# Fetch all completed landings
	lCompleted = Record_MySQL.Commands.select(
		"monolith_prod",
		LANDING_SQL,
		Record_MySQL.ESelect.COLUMN
	)

	# Go through them 100 at a time
	iCount = 0;
	while True:

		print('\rWorking on %d' % iCount, end='')

		# Get 100 IDs
		lIDs = lCompleted[iCount:(iCount+100)]

		# If there's none
		if len(lIDs) == 0:
			break

		# Fetch the answers for the slice
		dValues = {
			d['landing_id']:d['value']
			for d in Record_MySQL.Commands.select(
				"monolith_prod",
				VALUE_SQL % '","'.join(lIDs),
				Record_MySQL.ESelect.ALL
			)
		}

		# Go through each landing ID
		for sID in lIDs:

			# Get the lowercase value
			try: v = dValues[sID].lower()
			except: v = '';

			# Increment the value
			try: dDistinct[v] += 1
			except: dDistinct[v] = 1

		# Increase the count
		iCount += 100

	print('')
	print('Found %d completed landings' % len(lCompleted))
	print('Found %d with None/Blank' % (dDistinct['none'] + dDistinct['']))

	with open('./reports/files/distinct_allergies.csv', 'w') as oF:
		for v,i in dDistinct.items():
			oF.write('"%s",%d\n' % (v.replace('"', '""'), i))
