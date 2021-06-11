# coding=utf8
"""Ticket Stats

Holds the generic methods for gathering and storing stats
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-06-10"

# Record imports
from records.csr import Agent, TicketOpened, TicketResolved, TicketStat

# Constants
AGENT_TYPES = ['agent', 'pa', 'on_hrt']
ACTION_TYPES = [
	['opened', TicketOpened],
	['resolved', TicketResolved]
]

def getAndStore(range_type, date, start, end):
	""" Get and Store

	Gets the counts by type and user for the given start/end and stores them
	under the given range type

	Arguments:
		range_type (str): The range type, day, week, or month
		date (str): The date to store the counts under
		start (uint): The starting timestamp for the counts
		end (uint): The ending timestamp for the counts

	Returns:
		None
	"""

	# Go through each type and fetch the Memo IDs associated
	dTypes = {}
	for s in AGENT_TYPES:
		dTypes[s] = Agent.memoIdsByType(s)

	# Go through each action type
	for l in ACTION_TYPES:

		# Go through each agent type
		for s in AGENT_TYPES:

			# If we have any memo IDs in the list
			if dTypes[s]:

				# Get the count of the action type in the given time frame with the
				#	Memo IDs in the given agent type
				iCount = l[1].count(filter={
					"_created": {"between": [start, end]},
					"memo_id": dTypes[s]
				})

				# Save it in the DB
				oStat = TicketStat({
					"range": range_type,
					"date": date,
					"list": s,
					"action": l[0],
					"count": iCount
				})
				oStat.create(conflict='replace')

		# Get the counts by user
		lCounts = l[1].counts(start, end)

		# Add each one to the DB
		for d in lCounts:

			# Save it in the DB
			oStat = TicketStat({
				"range": range_type,
				"date": date,
				"memo_id": d['memo_id'],
				"action": l[0],
				"count": d['count']
			})
			oStat.create(conflict='replace')

	# Return OK
	return True
