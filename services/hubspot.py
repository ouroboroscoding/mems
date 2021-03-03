# coding=utf8
""" HubSpot Service

Handles all HubSpot requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-11-12"

# Python imports
import urllib.parse

# Pip imports
import requests
from RestOC import Conf, DictHelper, JSON, Services

class HubSpot(Services.Service):
	"""HubSpot Service class

	Service for HubSpot CRM access
	"""

	def _list(self, val):
		"""List

		Returns the ID of a list based on the text passed, or else the default

		Arguments:
			val (str): The value associated with the list ID

		Returns:
			uint
		"""
		try: return self._lists[val]
		except: return self._lists['_']

	def _post(self, path, properties):
		"""Post

		Sends a POST request

		Arguments:
			path (str): The URI/Noun to request
			properties (dict): The list of key/value pairs to send with the request

		Returns:
			mixed
		"""

		# Body
		sBody = JSON.encode({
			"properties": {[
				{"property": k, "value": v} for k,v in properties.items()
			]}
		})

		# Headers
		dHeaders = {
			"Content-Type": "application/json",
			"Content-Length": str(len(sData))
		}

		# Generate URL
		sURL = 'https://%s/path?hapikey=%s' % (
			self._conf['domain'],
			urllib.parse.urlencode(self._conf['api_key'])
		)

		# Make the request
		oRes = requests.post(sURL, data=sBody, headers=dHeaders)

		# If we got a 200 back
		if oRes.status == 200:
			return oRes.json()

		# Else, if we got a 204
		elif oRes.status == 204:
			return True

		# Else, we failed somehow
		else:
			print(oRes.text)
			return False

	def _request(self, path, properties):
		"""Request

		Makes a GET request

		Arguments:
			path (str): The URI/Noun to request
			properties (dict): The list of key/value pairs to send with the request

		Returns:
			mixed
		"""

		# Body
		sBody = JSON.encode({
			"properties": {[
				{"property": k, "value": v} for k,v in properties.items()
			]}
		})

		# Headers
		dHeaders = {
			"Content-Type": "application/json"
		}

		# Generate URL
		sURL = 'https://%s/path?hapikey=%s' % (
			self._api['domain'],
			urllib.parse.urlencode(self._api['key'])
		)

		# Make the request
		oRes = requests.get(sURL, data=sBody, headers=dHeaders)

		# If we got a 200 back
		if oRes.status == 200:
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
		self._api = Conf.get(('hubspot', 'api'))
		self._lists = Conf.get('hubspot', 'lists', {'_': 545})

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

	def customerDecline_update(self, data):
		"""Customer Decline

		Adds a customer to a decline list and adds the decline_reason property

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'type'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Must have one of vid or email
		if 'vid' not in data and 'email' not in data:
			return Services.Response(error=(1001, [('vid', 'missing'), ('email', 'missing')]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Get the list
		iList = self._list(data['type'])

		# Set properties and contact path based on vid or email
		if 'vid' in data:
			dProperties = {"vids": [data['vid']]}
			sContactPath = 'contacts/v2/contact/vid/%s/profile' % str(data['vid'])
		else:
			dProperties = {"email": [data['email']]}
			sContactPath = 'contacts/v2/contact/email/%s/profile' % data['email']

		# List path
		sListPath = 'contacts/v1/lists/%d/add' % iList

		# Update the list
		if not self._post(sListPath, dProperties):
			return Services.Response(False)

		# Update the customer
		return Services.Response(
			self._post(sContactPath, {
				"decline_reason": data['type']
			})
		)

	def customerLabel_update(self, data):
		"""Customer Label

		Sets the label for a customer

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'label'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Must have one of vid or email
		if 'vid' not in data and 'email' not in data:
			return Services.Response(error=(1001, [('vid', 'missing'), ('email', 'missing')]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# If we got a vid
		if 'vid' in data:
			sPath = 'contacts/v2/contact/vid/%s/profile' % str(data['vid'])
		else:
			sPath = 'contacts/v2/contact/email/%s/profile' % data['email']

		# Make the request and return the result
		return Services.Response(
			self._post(sPath, {
				"order_label": data['label']
			})
		)
