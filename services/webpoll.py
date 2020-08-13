# coding=utf8
""" Web Poll Service

Handles syncing through long polling between services and DB
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2019-03-29"

# Python imports
import json
from time import time

# Pip imports
from redis import StrictRedis
from RestOC import Conf, DictHelper, Services, Sesh, StrHelper

# Shared imports
from shared import Sync

# WebPoll class
class WebPoll(Services.Service):
	"""Polling Service class

	Service for long polling between connected clients and the DB
	"""

	def clear_update(self, data, sesh):
		"""Clear

		Clears the given number of messages from the sync cache

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['service', 'key', 'count'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Clear the messages from the sync cache
		Sync.clear(
			sesh.id(),
			data['service'],
			data['key'],
			data['count']
		)

		# Return OK
		return Services.Effect(True)

	def join_create(self, data, sesh):
		"""Join

		Connects a session to an account or contact so that any messages
		associated with either are stored for later polling

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['service', 'key'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Update the sync cache
		Sync.join(
			sesh.id(),
			data['service'],
			data['key']
		)

		# Return OK
		return Services.Effect(True)

	def leave_create(self, data, sesh):
		"""Leave

		Disconnects a session from an account or contact so that messages are
		no longer collected for it

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['service', 'key'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Update the sync cache
		Sync.leave(
			sesh.id(),
			data['service'],
			data['key']
		)

		# Return OK
		return Services.Effect(True)

	def pull_read(self, data, sesh):
		"""Pull

		A client is requesting an update on anything they might be looking at

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['service', 'key'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# If we have messages to delete
		if 'messages' in data and data['messages']:
			Sync.clear(
				sesh.id(),
				data['service'],
				data['key'],
				data['messages']
			)

		# Get as many messages as possible
		lRet = Sync.pull(
			sesh.id(),
			data['service'],
			data['key']
		)

		# Return whatever was found
		return Services.Effect(lRet)

	def websocket_read(self, data, sesh):
		"""WebSocket

		Generates a unique key for the client that it can use to authorize a
		websocket connection

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Generate a random key
		sKey = StrHelper.random(32, ['aZ', '10', '!'])

		# Store the key in the sync cache
		Sync.socket(sKey, {
			"session": sesh.id()
		})

		# Return the key
		return Services.Effect(sKey)

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			WebPoll
		"""

		# Init the sync module
		Sync.init(Conf.get(('redis', 'sync'), {
			"host": "localhost",
			"port": 6379,
			"db": 1
		}))

		# Return self
		return self
