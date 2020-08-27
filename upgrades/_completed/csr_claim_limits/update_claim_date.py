# coding=utf8
""" Create the List tables"""

# Pip imports
from RestOC import Record_MySQL

# Record imports
from records.monolith import CustomerClaimed

def run():

	# Update the created date of all claims
	CustomerClaimed.updateField(
		'updatedAt',
		Record_MySQL.Literal('CURRENT_TIMESTAMP')
	)

	# Return OK
	return True
