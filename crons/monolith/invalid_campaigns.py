# coding=utf8
"""Invalid Campaigns

Looks for orders with campaigns not currently in the system
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-10-22"

# Pip imports
from RestOC import Services

# Record imports
from records.monolith import Campaign, KtOrder

# Cron imports
from crons import emailError

def run():
	"""Run

	Fetches distinct campaign IDs in orders and compares them to the campaign
	table to look for any campaigns not currently set to a type

	Returns:
		bool
	"""

	# Fetch distinct campaign IDs in orders
	lOrderIDs = KtOrder.distinctCampaigns()

	# Get the list of campaign IDs
	lCampaignIDs = Campaign.ids()

	# Get the difference
	lDiff = list(set(lOrderIDs) - set(lCampaignIDs))

	# If we find any
	if lDiff:

		# Get the list of recipients for the report
		oResponse = Services.read('reports', 'recipients/internal', {
			"_internal_": Services.internalKey(),
			"name": 'Campaigns_Missing'
		})
		if oResponse.errorExists():
			emailError('Invalid Campaigns Failed', 'Failed to get report recipients\n\n%s' % (
				str(oResponse)
			))
			return False

		# Generate the email
		sContent = "The following campaign IDs have no associated type, i.e. ED, HRT, etc\n\n" \
					"%s\n\n" \
					"Please login to https://admin.meutils.com/ and add the campaigns" % ', '.join(lDiff)

		# Send the email
		oResponse = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"text_body": sContent,
			"subject": 'MISSING CAMPAIGNS',
			"to": oResponse.data
		})
		if oResponse.errorExists():
			emailError('Invalid Campaigns Failed', 'Failed to send email\n\n%s\n\n' % (
				str(oResponse),
				sContent
			))
			return False
