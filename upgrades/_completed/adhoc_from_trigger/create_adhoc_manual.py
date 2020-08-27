# coding=utf8
""" Alter the adhoc table"""

# Pip imports
from RestOC import Record_MySQL

# Service imports
from records.welldyne import AdHocManual

def run():

	AdHocManual.tableCreate()
	return True
