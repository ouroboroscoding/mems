# coding=utf8
"""Update Resolution Sesh

Finds the appropriate session to set based on the type of action
"""

# Pip imports
import arrow

# Service Records
from records.providers import Tracking

def run():

	# Finds all the signins with a signout
	l = Tracking.filter({
		"action": "signin",
		"resolution": "signout"
	})

	# Go through each one and set the resolution sesh to the action sesh
	for o in l:
		o['resolution_sesh'] = o['action_sesh']
		o.save()

	# Find all signins with new_signin
	l = Tracking.filter({
		"action": "signin",
		"resolution": "new_signin"
	})

	# Go through each one
	for o in l:

		# Find the next signin
		dSignin = Tracking.filter({
			"memo_id": o['memo_id'],
			"action": 'signin',
			"action_ts": {"gte": o['resolution_ts']}
		}, orderby='action_ts', limit=1)

		# If it exists, set the session
		if dSignin:
			o['resolution_sesh'] = dSignin['action_sesh']
			o.save()

	# Find all viewed
	l = Tracking.filter({
		"action": "viewed"
	})

	# Go through each one
	for o in l:

		# If it doesn't have a resolution yet, skip it
		if o['resolution'] is None:
			continue

		# Find the oldest signin before this action
		dSignin = Tracking.filter({
			"memo_id": o['memo_id'],
			"action": 'signin',
			"action_ts": {"lt": o['resolution_ts']}
		}, orderby=[['action_ts', 'DESC']], limit=1)

		# If it exists, set the session
		if dSignin:
			o['resolution_sesh'] = dSignin['action_sesh']
			o.save()

	# Return OK
	return True
