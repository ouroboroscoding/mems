# coding=utf8
""" WellDyne Eligibility Update

Finds all eligibilities
"""

# Python imports
import os, platform, sys

# Pip imports
import requests

# Framework imports
from RestOC import Conf, Record_MySQL

# Only run if called directly
if __name__ == "__main__":

	# Check arguments
	if len(sys.argv) != 2:
		print('This tool requires a new date to set to')
		sys.exit(1)

	# Load the config
	Conf.load('config.json')
	sConfOverride = 'config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Add hosts
	Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))

	# Get Memo config
	dMemo = Conf.get('memo')

	# Create a requests session
	oHttp = requests.Session()

	# Login to memo
	oRes = oHttp.post('https://%s/users/login' % dMemo['domain'], data={
		"username": dMemo['user'],
		"password": dMemo['pass']
	}, allow_redirects=False)

	print(oRes)

	# Fetch all Eligibilities in the past
	lElig = Record_MySQL.Commands.select(
		'monolith',
		'SELECT `id`, `memberSince`, `memberThru` ' \
		'FROM `monolith`.`wd_eligibility` ' \
		'WHERE `memberThru` != \'0000-00-00 00:00:00\' ' \
		'AND `memberThru` < ADDDATE(NOW(), INTERVAL 2 DAY)'
	)

	# Go through each one
	for d in lElig:

		print(d)

		# Split the memberSince into date and time
		lDT = d['memberSince'].split(' ')

		print({
			"memberSince": "%sT%s.000Z" % (lDT[0], lDT[1]),
			"memberThru": "%sT00:00:00.000Z" % sys.argv[1]
		})

		# Send a request to Memo to update the record
		oRes = oHttp.post('https://%s/welldyne/eligibility/%d' % (Conf.get(('memo', 'domain')), d['id']), data={
			"memberSince": "%sT%s.000Z" % (lDT[0], lDT[1]),
			"memberThru": "%sT00:00:00.000Z" % sys.argv[1]
		})

		print(oRes.status_code)
		print(oRes.content)

	# Exit
	sys.exit(0)
