# coding=utf8
""" Create the ticket tables"""

# Pip imports
from RestOC import Record_MySQL

# Service imports
from records.csr import Ticket, TicketAction, TicketItem, TicketOpened, TicketResolved

def run():

	Ticket.tableCreate()
	TicketOpened.tableCreate()
	TicketAction.tableCreate()
	TicketItem.tableCreate()
	TicketResolved.tableCreate()
	return True
