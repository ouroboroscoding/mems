# coding=utf8
""" Create the ticket tables"""

# Pip imports
from RestOC import Record_MySQL

# Service imports
from records.csr import Ticket, TicketAction, TicketItem

def run():

	Ticket.tableCreate()
	TicketAction.tableCreate()
	TicketItem.tableCreate()
	return True
