# coding=utf8
""" Add read permissions to all agents"""

# Pip imports
from redis import StrictRedis
from RestOC import Conf, Record_MySQL

def run():

	# Fetch the IDs of all agents
	lIDs = Record_MySQL.Commands.select(
		'primary',
		'SELECT `_id` FROM `mems`.`csr_agent`',
		Record_MySQL.ESelect.COLUMN
	)

	# Generate the inserts
	lInserts = []
	for _id in lIDs:
		lInserts.append("('%s', 'campaigns', 1)" % _id)
		lInserts.append("('%s', 'products', 1)" % _id)

	# Generate the full SQL
	sSQL = 'INSERT INTO `mems`.`auth_permission` ' \
			'(`user`, `name`, `rights`)\n' \
			'VALUES %s' % ',\n'.join(lInserts)

	# Insert the records
	Record_MySQL.Commands.execute(
		'primary',
		sSQL
	)

	# Connect to Redis
	redis = StrictRedis(**Conf.get(('redis', 'primary'), {
		"host": "localhost",
		"port": 6379,
		"db": 0
	}))

	# Go through each agnet and clear the permissions
	for _id in lIDs:
		redis.delete('perms:%s' % _id)

	# Return OK
	return True
