# coding=utf8
""" Add permissions to every agent and provider"""

# Pip modules
from RestOC import Conf, Record_MySQL
from redis import StrictRedis

# Record modules
from records.csr import Agent
from records.providers import Provider

def run():

	# Connect to Redis
	redis = StrictRedis(**Conf.get(('redis', 'primary'), {
		"host": "localhost",
		"port": 6379,
		"db": 0
	}))

	# Find the ID of all agents
	lAgents = Agent.get(raw=['_id'])

	# Go through each one and add the permission
	for d in lAgents:
		Record_MySQL.Commands.execute(
			'primary',
			"INSERT IGNORE INTO `mems`.`auth_permission` (`user`, `name`, `rights`) VALUES " \
			"('%s', 'rx_diagnosis', 1)" % d['_id']
		)

		# Clear the user's permissions
		redis.delete('perms:%s' % d['_id'])

	# Find the ID of all providers
	lProviders = Provider.get(raw=['_id'])

	# Go through each one and add the permission
	for d in lProviders:
		Record_MySQL.Commands.execute(
			'primary',
			"INSERT IGNORE INTO `mems`.`auth_permission` (`user`, `name`, `rights`) VALUES " \
			"('%s', 'rx_diagnosis', 1)" % d['_id']
		)

		# Clear the user's permissions
		redis.delete('perms:%s' % d['_id'])

	# Return OK
	return True
