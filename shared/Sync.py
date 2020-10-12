# coding=utf8
""" Sync Module

Holds methods for storing and fetching messages from the sync storage
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2018-09-09"

# Include pip modules
from redis import StrictRedis
from RestOC import Conf, JSON

# The redis instance
_moRedis = None

# init function
def init():
	"""Initialise

	Initializes the Redis connection so that sync can be fetched and saved

	Args:
		conf (dict): The configuration needed to connect to redis
	"""

	# Import the redis instance
	global _moRedis

	# Get the config
	dConf = Conf.get(('redis', 'sync'))

	# Initialise the connection to Redis
	_moRedis = StrictRedis(**dConf)

# clear function
def clear(auth, service, key, count):
	"""Clear

	Removes the given count of messages from the sync cache

	Args:
		auth (str): The session authorization key
		service (str): The name of the service using the sync
		key (str): The unique key of the message list
		count (uint): The number of messages to clear
	"""

	# Make sure the service and key are strings
	if not isinstance(service, str): service = str(service)
	if not isinstance(key, str): key = str(key)

	# Generate the key name
	sKey = '%s-%s%s' % (auth, service, key)

	# If we have messages to delete
	if count == 1:
		_moRedis.rpop(sKey);
	else:
		oPipeline = _moRedis.pipeline()
		for __ in range(count):
			oPipeline.rpop(sKey);
		oPipeline.execute()

# join function
def join(auth, service, key):
	"""Join

	Called to add a session to the sync cache

	Args:
		auth (str): The session authorization key
		service (str): The name of the service using the sync
		key (str): The unique key of the message list

	Returns: None
	"""

	# Make sure the service and key are strings
	if not isinstance(service, str): service = str(service)
	if not isinstance(key, str): key = str(key)

	# Add the key to the set and extend the ttl
	p = _moRedis.pipeline()
	p.sadd('%s%s' % (service, key), "%s-%s%s" % (auth, service, key))
	p.expire(key, 21600)
	p.execute()

# leave function
def leave(auth, service, key):
	"""Leave

	Called to remove a session from the sync cache

	Args:
		auth (str): The session authorization key
		service (str): The name of the service using the sync
		key (str): The unique key of the message list

	Returns: None
	"""

	# Make sure the key is a string
	if not isinstance(key, str): key = str(key)

	# Remove the key from the set
	_moRedis.srem('%s%s' % (service, key), "%s-%s%s" % (auth, service, key))

# pull function
def pull(auth, service, key):
	"""Pull

	Fetches and returns as many messages are in the sync cache for the given
	authorization key and message list key

	Args:
		auth (str): The session authorization key
		service (str): The name of the service using the sync
		key (str): The unique key of the message list

	Returns:
		list
	"""

	# Make sure the service and key are strings
	if not isinstance(service, str): service = str(service)
	if not isinstance(key, str): key = str(key)

	# Generate the key name
	sKey = '%s-%s%s' % (auth, service, key)

	# Get the current length of messages
	iLen = _moRedis.llen(sKey)

	# Update the TTL on the session
	bRes = _moRedis.expire('%s%s' % (service, key), 21600) # 6 hours

	# If the key doesn't even exist anymore
	if not bRes:
		return False

	# If any messages exist
	if iLen:

		# Fetch them
		lRet = _moRedis.lrange(sKey, 0, iLen)

		# Reverse the list
		lRet.reverse()

		# Return the decoded messages
		return [JSON.decode(s) for s in lRet]

	# Return an empty list
	else:
		return []

# push function
def push(service, key, data):
	"""Push

	Called to push data to the sync cache

	Args:
		service (str): The name of the service using the sync
		key (mixed): The key to push the data onto
		data (mixed): The data to be pushed

	Returns:
		bool|string
	"""

	# Make sure the service and key are strings
	if not isinstance(service, str): service = str(service)
	if not isinstance(key, str): key = str(key)

	# Generate the JSON
	sJSON = JSON.encode({
		"service": service,
		"key": key,
		"data": data
	})

	# Check if anyone is interested in the key
	lSessions = _moRedis.smembers("%s%s" % (service, key))

	# If there are any sessions
	if lSessions:

		# For each session found
		for sSession in lSessions:

			# Add the message to its list
			p = _moRedis.pipeline()
			p.lpush(sSession, sJSON)
			p.expire(sSession, 21600)
			p.execute()

	# Now publish the message for anyone using websockets
	_moRedis.publish("%s%s" % (service, key), sJSON)

	# Return OK
	return True

# socket function
def socket(key, data):
	"""Socket

	Called to store a key used to validate the socket connection

	Args:
		key (str): The key used to authenticate the socket connection
		data (dict): The data to store in the key

	Returns:
		None
	"""

	# Make sure the service and key are strings
	if not isinstance(key, str): key = str(key)

	# Create the key and make it expire in 10 seconds
	_moRedis.setex(key, 10, JSON.encode(data))
