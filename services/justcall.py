# coding=utf8
""" JustCall Service

Handles all JustCall requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-02-22"

# Python imports
from operator import itemgetter
from time import sleep
import urllib.parse

# Pip imports
import requests
from RestOC import Conf, DictHelper, JSON, Services

# Records imports
from records.justcall import MemoId

# Shared imports
from shared import Rights

# Call Types
_CALL_TYPES = {
	"1": "All",
	"2": "Outbound",
	"3": "Inbound",
	"4": "Missed",
	"5": "Voicemails"
}

class JustCall(Services.Service):
	"""JustCall Service class

	Service for JustCall CRM access
	"""

	_install = [MemoId]
	"""Record types called in install"""

	@classmethod
	def install(cls):
		"""Install

		The service's install method, used to setup storage or other one time
		install configurations

		Returns:
			bool
		"""

		# Go through each Record type
		for o in cls._install:

			# Install the table
			if not o.tableCreate():
				print("Failed to create `%s` table" % o.tableName())

		# Return OK
		return True

	def _all(self, path, data):
		"""All

		Sends a POST request for all records

		Arguments:
			path (str): The URI/Noun to request
			data (dict): The list of key/value pairs to send with the request

		Returns:
			mixed
		"""

		# Init the return
		lRet = []

		# Add the page and count per page
		data['page'] = 1
		data['per_page'] = 100

		# Headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": '%s:%s' % (
				self.conf['key'],
				self.conf['secret']
			)
		}

		# Generate URL
		sURL = 'https://api.justcall.io/v1/%s' % path

		# Make sure we get every page
		while True:

			# Body
			sBody = JSON.encode(data)

			# Send the data
			iAttempts = 0
			while True:
				try:
					oRes = requests.post(sURL, data=sBody, headers=dHeaders, timeout=10)
					break
				except requests.exceptions.ConnectionError as e:
					iAttempts += 1
					if iAttempts < 3:
						sleep(1)
						continue
					raise e

			# If we got a 200 back
			if oRes.status_code == 200:

				# Pull out the data
				dData = oRes.json()

				# If we didn't get success
				if dData['status'] != 'success':
					break

				# Add the data to the result
				lRet.extend(dData['data'])

				# If we got less than a hundred
				if len(dData['data']) < 100:
					break

				# Increment the page
				data['page'] += 1

			# Else, we failed somehow
			else:
				print(oRes.text)
				return False

		# Return the found data
		return lRet

	def _one(self, path, data):
		"""One Record

		Sends a POST request for one record

		Arguments:
			path (str): The URI/Noun to request
			data (dict): The list of key/value pairs to send with the request

		Returns:
			mixed
		"""

		# Body
		sBody = JSON.encode(data)

		# Headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": '%s:%s' % (
				self.conf['key'],
				self.conf['secret']
			)
		}

		# Generate URL
		sURL = 'https://api.justcall.io/v1/%s' % path

		# Send the data
		iAttempts = 0
		while True:
			try:
				oRes = requests.post(sURL, data=sBody, headers=dHeaders, timeout=10)
				break
			except requests.exceptions.ConnectionError as e:
				iAttempts += 1
				if iAttempts < 3:
					sleep(1)
					continue
				raise e

		# If we got a 200 back
		if oRes.status_code == 200:
			dRes = oRes.json()
			return dRes['data']

		# Else, we failed somehow
		else:
			print(oRes.text)
			return False

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Store config data
		self.conf = Conf.get(('justcall'))

		# Return self for chaining
		return self

	@classmethod
	def install(cls):
		"""Install

		The service's install method, used to setup storage or other one time
		install configurations

		Returns:
			bool
		"""
		return True

	def log_read(self, data, sesh=None):
		"""Log

		Returns a single log by ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.internalOrCheck(data, sesh, 'justcall', Rights.READ)

		# If the ID is missing
		if 'id' not in data:
			return Services.Error(1001, [('id', 'missing')])

		# Are we in multiple mode?
		if isinstance(data['id'], list):
			bMultiple = True
		else:
			bMultiple = False
			data['id'] = [data['id']]

		# Init the results
		lResults = []

		# For each ID
		for iID in data['id']:

			# Make the request
			dRes = self._one('calls/get', {
				"id": iID
			})

			# Add the text version of the call type
			dRes['typeText'] = _CALL_TYPES[dRes['type']]

			# Store it
			lResults.append(dRes)

		# Return the data received
		return Services.Response(bMultiple and lResults or lResults[0])

	def logs_read(self, data, sesh):
		"""Logs

		Returns all logs by phone number

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'justcall', Rights.READ)

		# If a phone number is missing
		if 'phone' not in data:
			return Services.Error(1001, [('phone', 'missing')])

		# If the length of the number is 11
		if len(data['phone']) == 11:
			data['phone'] = '+%s' % data['phone']

		# Else, if it's 10
		elif len(data['phone']) == 10:
			data['phone'] = '+1%s' % data['phone']

		# Make the request
		lRes = self._all('calls/query', {
			"contact_number": data['phone'],
			"order": "ASC",
			"per_page": 100,
			"type": '1'
		})

		# If we have no data
		if not lRes:
			return Services.Response([])

		# If we don't have a type
		if 'types' not in data:
			data['types'] = []

		# Else, make sure we have a list
		elif not isinstance(data['types'], list):
			data['types'] = [data['types']]

		# Init the return list and the set of agents
		lRet = []
		lAgents = set()

		# Go through each call
		for d in lRes:

			# Add the text version of the call type
			d['typeText'] = _CALL_TYPES[d['type']]

			# If we want all or the type is in the list
			if not data['types'] or d['type'] in data['types']:

				# Add the agent to the set
				lAgents.add(d['agent_id'])

				# Add the log to the return
				lRet.append(d)

		# Get the list of Memo IDs associated with the agents
		dAgents = {
			d['agent_id']:d['memo_id'] for d in
			MemoId.get(list(lAgents), raw=True)
		}

		# Go through each call and add the memo ID
		for d in lRet:
			if d['agent_id'] in dAgents:
				d['memo_id'] = dAgents[d['agent_id']]

		# Return the data received
		return Services.Response(lRet)

	def users_read(self, data, sesh):
		"""Users

		Returns the list of Users and their IDs in JustCall

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'justcall', Rights.READ)

		# Make the request
		lRes = self._all('users/list', {})

		# Store just the relevant info
		lUsers = [{
			'agent_id': d['agent_id'],
			'firstName': d['firstname'],
			'lastName': d['lastname']
		} for d in lRes]

		# Sort it by name and return it
		return Services.Response(sorted(lUsers, key=itemgetter('firstName', 'lastName')))
