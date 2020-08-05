# coding=utf8
""" Copy the triggers"""

# Python imports
import time

# Pip imports
import arrow

# Service imports
from services.konnektive import Konnektive
from services.welldyne.records import Trigger

# Cron imports
from crons.shared import PharmacyFill

def run():

	# Create a new Konnektive instance
	oKNK = Konnektive()
	oKNK.initialise()

	# Init the pharmacy fill module
	PharmacyFill.initialise()

	# Fetch all triggers with no order
	lTriggers = Trigger.filter({
		"crm_order": ''
	})

	# Go through each one found
	for o in lTriggers:

		print('Working on %s:%s' % (o['crm_type'], o['crm_id']))

		# Convert data
		lDT = arrow.get(o['_created']).format('MM/DD/YYYY HH:mm:ss').split(' ')

		# Ignore random KNK errors
		while True:
			try:

				# Find the latest order before this trigger was created
				lRes = oKNK._request('order/query', {
					"customerId": o['crm_id'],
					"orderStatus": 'COMPLETE',
					"sortDir": 0,
					"startDate": "01/01/2010",
					"startTime": "00:00:00",
					"endDate": lDT[0],
					"endTime": lDT[1]
				})

				# If we got a value
				if lRes:

					# Store the order ID
					o['crm_order'] = lRes[0]['orderId']

					# Try to process the data
					dRes = PharmacyFill.process({
						"crm_type": o['crm_type'],
						"crm_id": o['crm_id'],
						"crm_order": ''
					}, {
						"order": lRes[0],
						"max_date": o['_created']
					})

					# If it was successful
					if dRes['status']:

						print('\tSuccess, found %d records' % len(dRes['data']))

						# Update the RX and medication
						o['medication'] = dRes['data'][0]['medication']
						o['rx_id'] = str(dRes['data'][0]['ds_id'])

						# If we got more than one
						for d in dRes['data'][1:]:

							# Copy the existing instances data
							dRecord = o.record()

							# Delete the ID
							del dRecord['_id']

							# Add the medication and rx ID
							dRecord['medication'] = d['medication']
							dRecord['rx_id'] = str(d['ds_id'])

							# Create a new instance and store it in the DB
							oTrigger = Trigger(dRecord)
							oTrigger.create()

					else:
						print('\tFailed, %s' % dRes['data'])

					# Save the updated trigger
					o.save()

				# Break out of the loop
				break

			except Exception as e:
				print(e)
				print([str(s) for s in e.args])
				time.sleep(1)

