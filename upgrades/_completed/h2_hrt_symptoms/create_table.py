# coding=utf8
""" Create the monolith `hormone_symptoms_to_questions` table"""

# Services
from records.monolith import HormoneSymptomToQuestion

def run():

	# Create the tables
	HormoneSymptomToQuestion.tableCreate()

	# Return OK
	return True
