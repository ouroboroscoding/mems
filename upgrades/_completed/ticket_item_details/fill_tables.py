# coding=utf8
""" Update all the ticket item records to add the direction and memo ID"""

# Pip imports
from RestOC import Record_MySQL

# Service imports
from services.justcall import JustCall

# Record imports
from records.justcall import MemoId
from records.monolith import User

def run():

	# Create a JustCall instance
	oJustCall = JustCall()
	oJustCall.initialise()

	# Fetch all the agents
	lAgents = oJustCall._all('users/list', {})

	# Go through each one
	for d in lAgents:

		# Try to find the user
		dUser = User.filter({
			"firstName": d['firstname'],
			"lastName": d['lastname']
		}, raw=['id'], limit=1)

		# If we found a user
		if dUser:

			# Create a new bridge record
			oMemoId = MemoId({
				"agent_id": d['agent_id'],
				"memo_id": dUser['id']
			})
			oMemoId.create(conflict='ignore')

	# Return OK
	return True
