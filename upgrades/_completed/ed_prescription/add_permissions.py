# coding=utf8
""" Add permissions to every provider"""

# Pip modules
from RestOC import Conf, Record_MySQL
from redis import StrictRedis

def run():

	# Connect to Redis
	redis = StrictRedis(**Conf.get(('redis', 'primary'), {
		"host": "localhost",
		"port": 6379,
		"db": 0
	}))

	# Find all existing 'order_claims' permissions
	lPerms = Record_MySQL.Commands.select(
		'primary',
		"SELECT `user` FROM `mems`.`auth_permission` " \
		"WHERE `name` = 'order_claims'"
	)

	# Go through each one and add the other permissions
	for d in lPerms:
		Record_MySQL.Commands.execute(
			'primary',
			"INSERT IGNORE INTO `mems`.`auth_permission` (`user`, `name`, `rights`) VALUES " \
			"('%s', 'rx_product', 1)" % d['user']
		)

		# Clear the user's permissions
		redis.delete('perms:%s' % d['user'])

	# Return OK
	return True
