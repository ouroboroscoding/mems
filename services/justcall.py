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
from time import sleep
import urllib.parse

# Pip imports
import requests
from RestOC import Conf, DictHelper, JSON, Services

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

	def _post(self, path, data):
		"""Post

		Sends a POST request

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
				oRes = requests.post(sURL, data=sBody, headers=dHeaders)
				break
			except requests.exceptions.ConnectionError as e:
				iAttempts += 1
				if iAttempts < 3:
					sleep(1)
					continue
				raise e

		# If we got a 200 back
		if oRes.status_code == 200:
			return oRes.json()

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

	def log_read(self, data, sesh):
		"""Log

		Returns a single log by ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'justcall', Rights.READ)

		# If the ID is missing
		if 'id' not in data:
			return Services.Error(1001, [('id', 'missing')])

		# Make the request
		dRes = self._post('calls/get', {
			"id": data['id']
		})

		# If the request failed
		if dRes == False:
			return Services.Error(2100, '404')

		# Add the text version of the call type
		dRes['data']['typeText'] = _CALL_TYPES[dRes['data']['type']]

		# Return the data received
		return Services.Response(dRes['data'])

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
		dRes = self._post('calls/query', {
			"contact_number": data['phone'],
			"order": "ASC",
			"per_page": 100
		})

		# If the request failed
		if dRes == False:
			return Services.Error(2100, '404')

		# Go through each call
		for d in dRes['data']:

			# Add the text version of the call type
			d['typeText'] = _CALL_TYPES[d['type']]

		# Return the data received
		return Services.Response(dRes['data'])
