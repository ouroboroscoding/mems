# coding=utf8
""" Create the Stat table"""

# Service imports
from records.csr import TicketStat

def run():

	TicketStat.tableCreate()
	return True
