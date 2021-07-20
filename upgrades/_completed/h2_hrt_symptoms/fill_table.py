# coding=utf8
""" Fill the table with insert records from the SQL file"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Open the SQL file and store the entire contents
	with open('upgrades/h2_hrt_symptoms/inserts.sql') as oF:
		sSQL = oF.read()

		# Modify the table
		Record_MySQL.Commands.execute(
			'primary',
			sSQL
		)

	# Return OK
	return True
