# coding=utf8
""" Create necessary tables"""

# Service imports
from records.prescriptions import HrtOrder

def run():

	# Delete it if it already exists
	try: HrtOrder.tableDrop()
	except: pass

	# Create the table
	HrtOrder.tableCreate()

	# Return OK
	return True
