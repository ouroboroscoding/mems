# coding=utf8
"""Update Shipped

Fetch all onboarding patients that are pre-H2 and see if their kit has been
shipped and update the hrt_patient table accordingly
"""

# Services
from records.monolith import HrtPatient, ShippingInfo

def run():
	"""Run

	Main entry point into the script

	Returns:
		None
	"""

	# Fetch all HRT patients that are still onboarding that are in the
	#	'Ordered Lab Kit' bucket
	lPatients = HrtPatient.filter({
		"stage": 'Onboarding',
		"processStatus": 'Ordered Lab Kit'
	})

	# Count
	iCount = 0

	# Go through each patient
	for o in lPatients:

		# Look for a UPS tracking code associated with that customer
		dTracking = ShippingInfo.filter({
			"customerId": o['ktCustomerId'],
			"type": "UPS"
		}, limit=1)

		# If we found one
		if dTracking:

			# Update the process status
			o['processStatus'] = 'Shipped Lab Kit'
			o.save()

			iCount +=1
			print('\r%d' % iCount, end='')

	# Return OK
	return True
