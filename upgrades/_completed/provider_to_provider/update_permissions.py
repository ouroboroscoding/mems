# coding=utf8
""" Update permissions on every provider"""

# Pip modules
from RestOC import Conf, Record_MySQL
from redis import StrictRedis

# Record modules
from records.providers import Provider

def run():

	# Connect to Redis
	redis = StrictRedis(**Conf.get(('redis', 'primary'), {
		"host": "localhost",
		"port": 6379,
		"db": 0
	}))

	# Find the ID of all agents
	lProviders = Provider.get(raw=['_id'])

	# Go through each one and update the permission
	for d in lProviders:
		Record_MySQL.Commands.execute(
			'primary',
			"UPDATE `mems`.`auth_permission` SET\n" \
			"	`rights` = 14\n" \
			"WHERE `user` = '%s'\n" \
			"AND `name` = 'order_claims'" % d['_id']
		)

		# Clear the user's permissions
		redis.delete('perms:%s' % d['_id'])

	# Return OK
	return True
