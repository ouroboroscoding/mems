# coding=utf8
""" Konnektive Service

Handles all Konnektive requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-05-09"

# Python imports
import math
import urllib.parse

# Pip imports
import requests
from RestOC import Conf, DictHelper, Errors, Services

# Shared imports
from shared import JSON

class Konnektive(Services.Service):
	"""Konnektive Service class

	Service for Konnektive CRM access

	Extends: shared.Services.Service
	"""

	def __generateURL(self, path, params={}):
		"""Generate URL

		Takes a path and params and generates the full URL with query string

		Arguments:
			path {str} -- The path (without leading/trailing slashes)
			params {dict} -- Name/value query pairs

		Returns:
			str
		"""

		# Add the user and pass to the params
		params['loginId'] = self._user
		params['password'] = self._pass

		# Generate and return the URL
		return 'https://%s/%s/?%s' % (
			self._host,
			path,
			urllib.parse.urlencode(params)
		)

	def __request(self, path, params):
		"""Request

		Fetches every page of data for a specific query

		Arguments:
			path {str} -- The path of the http request
			params {dict} -- The query params for the request

		Returns:
			list
		"""

		# Init the return result and current page
		lRet = []
		iPage = 1

		# Set the results per page
		params['resultsPerPage'] = 200

		# Make sure we get every page
		while(True):

			# Set the current page
			params['page'] = iPage

			# Generate the URL
			sURL = self.__generateURL(path, params)

			# Fetch the data
			oRes = requests.post(sURL, headers={"Content-Type": 'application/json; charset=utf-8'})

			# Pull out the data
			dData = oRes.json()

			# If we don't get success
			if dData['result'] != 'SUCCESS':
				print(dData)
				break

			print(dData['message']['data'])

			# Add the data to the result
			lRet.extend(dData['message']['data'])

			# If we got the last page
			if math.ceil(dData['message']['totalResults'] / 200) == dData['message']['page']:
				break

			# Increment the page
			iPage += 1

		# Return the found transactions
		return lRet

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Store config data
		self._user = Conf.get(('konnektive', 'user'))
		self._pass = Conf.get(('konnektive', 'pass'))
		self._host = Conf.get(('konnektive', 'host'))

		# Store encounter types
		self._encounters = JSON.load('../definitions/encounter_by_state.json');

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

	def customer_read(self, data, sesh):
		"""Customer

		Fetches a customer's info by ID

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Make the request to Konnektive
		lCustomers = self.__request('customer/query', {
			"dateRangeType": "dateUpdated",
			"customerId": data['id'],
			"startDate": "01/01/2019",
			"endDate": "01/01/3000"
		});

		# If there's none
		if not lCustomers:
			return Services.Effect(0)

		# Return the customer
		return Services.Effect({
			"id": lCustomers[0]['customerId'],
			"billing": {
				"address1": lCustomers[0]['address2'],
				"address2": lCustomers[0]['address2'],
				"city": lCustomers[0]['city'],
				"company": lCustomers[0]['companyName'],
				"country": lCustomers[0]['country'],
				"name": lCustomers[0]['firstName'] + ' ' + lCustomers[0]['lastName'],
				"postalCode": lCustomers[0]['postalCode'],
				"state": lCustomers[0]['state']
			},
			"campaign": {
				"name": lCustomers[0]['campaignName'],
				"type": lCustomers[0]['campaignType']
			},
			"created": lCustomers[0]['dateCreated'],
			"email": lCustomers[0]['emailAddress'],
			"notes": lCustomers[0]['notes'],
			"phone": lCustomers[0]['phoneNumber'],
			"shipping": {
				"address1": lCustomers[0]['shipAddress2'],
				"address2": lCustomers[0]['shipAddress2'],
				"city": lCustomers[0]['shipCity'],
				"company": lCustomers[0]['shipCompanyName'],
				"country": lCustomers[0]['shipCountry'],
				"name": lCustomers[0]['shipFirstName'] + ' ' + lCustomers[0]['shipLastName'],
				"postalCode": lCustomers[0]['shipPostalCode'],
				"state": lCustomers[0]['shipState']
			},
			"updated": lCustomers[0]['dateUpdated']
		})

	def customerOrders_read(self, data, sesh):
		"""Customer Orders

		Fetches the orders for a customer

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Make the request to Konnektive
		lOrders = self.__request('order/query', {
			"dateRangeType": "dateUpdated",
			"customerId": data['id'],
			"sortDir": 0
		});

		print(lOrders)

		# Return what ever's found after removing unnecessary data
		return Services.Effect([{
			"billing": {
				"address1": dO['address1'],
				"address2": dO['address2'],
				"city": dO['city'],
				"company": dO['companyName'],
				"country": dO['country'],
				"name": dO['firstName'] + ' ' + dO['lastName'],
				"postalCode": dO['postalCode'],
				"state": dO['state']
			},
			"campaign": dO['campaignName'],
			"couponCode": dO['couponCode'],
			"date": dO['dateUpdated'],
			"email": dO['emailAddress'],
			"encounter": self._encounters[dO['state']],
			"id": dO['orderId'],
			"items": 'items' in dO and [{
				"campaign": dI['name'],
				"description": dI['productDescription'],
				"price": dI['price'],
				"shipping": dI['shipping']
			} for dI in dO['items'].values()] or [],
			"phone": dO['phoneNumber'],
			"price": dO['price'],
			"shipping": {
				"address1": dO['shipAddress1'],
				"address2": dO['shipAddress2'],
				"city": dO['shipCity'],
				"company": dO['shipCompanyName'],
				"country": dO['shipCountry'],
				"name": dO['shipFirstName'] + ' ' + dO['shipLastName'],
				"postalCode": dO['shipPostalCode'],
				"state": dO['shipState']
			},
			"status": dO['orderStatus'],
			"type": dO['orderType'],
			"totalAmount": dO['totalAmount']
		} for dO in lOrders])