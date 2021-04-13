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
from time import sleep
import urllib.parse

# Pip imports
from redis import StrictRedis
import requests
from RestOC import Conf, DictHelper, JSON, Services

class HubSpot(Services.Service):
	"""HubSpot Service class

	Service for HubSpot CRM access
	"""

	_emailCampaignKey = 'hubspot_email_campaign:%d'
	"""Template to make email campaign id"""

	def _emailCampaigns(self, ids):
		"""Email Campaigns

		Returns the names of HubSpot email campaigns

		Arguments:
			ids (uint[]): The IDs of the campaigns to fetch

		Returns:
			dict
		"""

		# Make sure IDs is a list
		if not isinstance(ids, list):
			ids = [ids]

		# Generate the list of cache keys
		lKeys = [self._emailCampaignKey % id for id in ids]

		# Look for all campaigns in the cache
		lCache = self._redis.mget(lKeys)

		# Init the return dictionary
		dRet = {}

		# Go through each one
		for i in range(len(lCache)):

			# If it's null
			if not lCache[i]:

				# Fetch it from HubSpot
				dRes = self._item('email/public/v1/campaigns/%d' % ids[i])

				# Encode it and store it in the cache for a week
				self._redis.setex(self._emailCampaignKey % ids[i], 604800, JSON.encode(dRes))

				# Add it to the dictionary
				dRet[ids[i]] = dRes

			# Else, decode it and add it to the dictionary
			else:
				dRet[ids[i]] = JSON.decode(lCache[i])

		# Return what was found
		return dRet

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
		sURL = 'https://%s/%s?hapikey=%s' % (
			self._conf['domain'],
			path,
			urllib.parse.urlencode(self._conf['api_key'])
		)

		# Make the request
		oRes = requests.post(sURL, data=sBody, headers=dHeaders)

		# If we got a 200 back
		if oRes.status_code == 200:
			return oRes.json()

		# Else, if we got a 204
		elif oRes.status_code == 204:
			return True

		# Else, we failed somehow
		else:
			print(oRes.text)
			return False

	def _item(self, path, properties={}):
		"""Item

		Makes a GET request for a single item

		Arguments:
			path (str): The URI/Noun to request
			properties (dict): The list of key/value pairs to send with the request

		Returns:
			dict
		"""

		# Add the hapikey to the properties
		properties['hapikey'] = self._api['key']

		# Headers
		dHeaders = {
			"Content-Type": "application/json"
		}

		# Generate URL
		sURL = 'https://%s/%s?%s' % (
			self._api['domain'],
			path,
			urllib.parse.urlencode(properties)
		)

		# Fetch the data
		iAttempts = 0
		while True:
			try:
				# Make the request
				oRes = requests.get(sURL, headers=dHeaders)
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

	def _list(self, path, properties, data_name):
		"""Lists

		Makes a GET request for a list of data

		Arguments:
			path (str): The URI/Noun to request
			properties (dict): The list of key/value pairs to send with the request
			data_name (str): The name of the actual data parameter so we can
								store the values

		Returns:
			mixed
		"""

		# Init the return result
		lRet = []

		# Add the hapikey to the properties
		properties['hapikey'] = self._api['key']

		# Headers
		dHeaders = {
			"Content-Type": "application/json"
		}

		# Make sure we get every page
		while(True):

			# Generate URL
			sURL = 'https://%s/%s?%s' % (
				self._api['domain'],
				path,
				urllib.parse.urlencode(properties)
			)

			# Fetch the data
			while True:
				iAttempts = 0
				try:
					# Make the request
					oRes = requests.get(sURL, headers=dHeaders)
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

				# Add the data to the result
				lRet.extend(dRes[data_name])

				# If there's no more data
				if dRes['hasMore'] == False:
					break

				# Else, store the offset
				properties['offset'] = dRes['offset']

			# Else, we failed somehow
			else:
				print(oRes.text)
				return False

		# Return the results
		return lRet;

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Create a connection to Redis
		self._redis = StrictRedis(**Conf.get(('redis', 'primary'), {
			"host": "localhost",
			"port": 6379,
			"db": 0
		}))

		# Store config data
		self._api = Conf.get(('hubspot', 'api'))
		self._lists = Conf.get(('hubspot', 'lists'), {'_': 545})

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

	def customerEmails_read(self, data, sesh):
		"""Customer Emails

		Returns the log of email event sent to a specific customer by email
		address

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If the email is missing
		if 'email' not in data:
			return Services.Error(1001, [['email', 'missing']])

		# Make the request to get the events
		lEvents = self._list('email/public/v1/events', {
			"recipient": data['email']
		}, 'events')

		# If it failed
		if lEvents is False:
			return Services.Error(2200)

		# Reverse the list
		lEvents.reverse()

		# Init the list of unique events
		dEvents = {}

		# Go through each event and store the newest one
		for d in lEvents:

			# If we didn't get the campaign yet
			if d['emailCampaignId'] not in dEvents:
				dEvents[d['emailCampaignId']] = {}

			# Turn the timestamp into seconds
			d['created'] = int(d['created'] / 1000)

			# Add the event by type
			dEvents[d['emailCampaignId']][d['type']] = d

		# Get the campaigns
		dCampaigns = self._emailCampaigns(list(dEvents.keys()))

		# Go through each email event
		for iCampaignId in dEvents:

			# Add the campaign
			dEvents[iCampaignId]['campaign'] = iCampaignId in dCampaigns and \
							dCampaigns[iCampaignId] or \
							None

		# Return the events
		return Services.Response(list(dEvents.values()))

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
