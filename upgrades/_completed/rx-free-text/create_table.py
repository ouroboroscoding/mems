# coding=utf8
""" Create necessary tables"""

# Service imports
from records.prescriptions import Diagnosis, HrtOrder

def run():

	# Create the table
	Diagnosis.tableCreate()

	# Delete the existing HrtOrder table and re-create it
	try: HrtOrder.tableDrop()
	except: pass
	HrtOrder.tableCreate()

	# Return OK
	return True
