# coding=utf8
"""HRT Join Date

Looks for hrt_patient records with no join date and finds the order in order
to set it
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-02-09"

# Pip imports
from RestOC import Services

# Record imports
from records.monolith import HrtPatient, Campaign, KtOrder

# Cron imports
from crons import emailError, isRunning

def run():
	"""Run

	Looks for hrt_patient records with no join date and finds the order in order
	to set it

	Returns:
		bool
	"""

	# If it's already running, skip it
	if isRunning('monolith_hrt_join_date'):
		return True

	# Find all HrtPatients with no join date
	lPatients = HrtPatient.filter({
		"joinDate": None
	})

	# If there's none
	if not lPatients:
		return True;

	# Fetch all ZRT campaigns
	lZRT = [str(d['id']) for d in Campaign.filter({"type": 'zrt'})]

	# Go through each one
	for o in lPatients:

		# Find the first ZRT order
		dOrder = KtOrder.filter({
			"customerId": o['ktCustomerId'],
			"campaignId": lZRT
		}, raw=['dateCreated'], orderby='dateCreated', limit=1)

		# Set the join date and save the record
		o['joinDate'] = dOrder and dOrder['dateCreated'] or '1970-01-01 00:00:00'
		o.save()

	# Return OK
	return True
