# coding=utf8
""" Create the Customers tables"""

# Pip imports
from RestOC import Conf
from redis import StrictRedis

# Records imports
from records.auth import Permission

def run():

	# Connect to Redis
	redis = StrictRedis(**Conf.get(('redis', 'primary'), {
		"host": "localhost",
		"port": 6379,
		"db": 0
	}))

	# Find all permissions called crm_customer
	lPerms = Permission.filter({
		"name": "crm_customers"
	})

	# Go through each permission, modify the name, then purge the current
	#	permissions from the cache for the associated user
	for o in lPerms:
		o['name'] = 'customers'
		o.save()
		redis.delete('perms:%s' % o['user'])

	# Return OK
	return True
