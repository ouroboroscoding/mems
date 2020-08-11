# coding=utf8
""" Create the additional permissions for the agents"""

# Pip modules
from RestOC import Conf, Record_MySQL
from redis import StrictRedis

# Services
from services.patient import Patient

def run():

	# Connect to Redis
	redis = StrictRedis(**Conf.get(('redis', 'primary'), {
		"host": "localhost",
		"port": 6379,
		"db": 0
	}))

	# Fetch all the welldyne_adhoc permissions as a base
	lPerms = Record_MySQL.Commands.select(
		'primary',
		"SELECT `user`, `rights` " \
			"FROM `mems`.`auth_permission` " \
			"WHERE `name` = 'welldyne_adhoc'"
	)

	# Go through each one and add the other permissions
	for d in lPerms:
		Record_MySQL.Commands.execute(
			'primary',
			"INSERT INTO `mems`.`auth_permission` (`user`, `name`, `rights`) VALUES " \
				"('%(user)s', 'csr_claims', %(claims)d), " \
				"('%(user)s', 'csr_messaging', 7), " \
				"('%(user)s', 'crm_customers', 1), " \
				"('%(user)s', 'memo_mips', 3), " \
				"('%(user)s', 'memo_notes', 5), " \
				"('%(user)s', 'prescriptions', 3)" % {
				"user": d['user'],
				"claims": (d['rights'] == 4 and 12 or 14)
			}
		)

		# Clear the user's permissions
		redis.delete('perms:%s' % d['user'])

	# Return OK
	return True
