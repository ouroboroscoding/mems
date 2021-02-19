# coding=utf8
"""Update Signin Resolution Timestamp

Look for signin actions with new_signin and adjust based on their last viewed
"""

# Pip imports
import arrow

# Service Records
from records.providers import Tracking

def run():

	# Find all signins/new_signins
	l = Tracking.filter({
		"action": "signin",
		"resolution": "new_signin"
	})

	# Go through each one
	for o in l:

		print('------------------')
		print('Orig: %s' % str(o))

		# Look for the oldest viewed in the same session
		d = Tracking.filter({
			"memo_id": o['memo_id'],
			"resolution_sesh": o['action_sesh'],
			"action": 'viewed'
		}, orderby=[['resolution_ts', 'DESC']], limit=1)

		# If there's none or it's not complete
		if not d or d['resolution_ts'] is None:

			# Set resolution_ts to 15 minutes past the start
			oEnd = arrow.get(o['action_ts'])
			oEnd = oEnd.shift(minutes=15)
			o['resolution_ts'] = oEnd.timestamp

		# Else, if there's one
		else:

			# Set the resolution_ts time to its resolution_ts time
			o['resolution_ts'] = d['resolution_ts']

		print('New:  %s' % str(o))

		# Save the record
		o.save()

	# Return OK
	return True
