# coding=utf8
"""Memo

Used to connect to Memo REST
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-04"

# Pip imports
import requests
from RestOC import Conf, DictHelper, JSON, Services

__funcToRequest = {
	'create': [requests.post, 'POST'],
	'delete': [requests.delete, 'DELETE'],
	'read': [requests.get, 'GET'],
	'update': [requests.put, 'PUT']
}
"""Map functions to REST types"""

def __request(action, path, data):
	"""Request

	Internal method to convert REST requests into HTTP requests

	Arguments:
		action {str} -- The action to take on the service
		path {str} -- The path of the request
		data {mixed} -- The data being sent with the request

	Return:
		mixed
	"""

	try: __funcToRequest[action]
	except KeyError: return {"error": {"code": Errors.SERVICE_ACTION, "msg": action}}

	# Get the config
	dConf = Conf.get('memo')

	# Generate the URL to reach the service
	sURL = "%s/%s?user=%s&pass=%s" % (
		dConf['domain'],
		path,
		dConf['user'],
		dConf['pass']
	)

	# Convert the data to JSON
	sData = JSON.encode(data)

	# Create the headers
	dHeaders = {
		'Content-Type': 'application/json; charset=utf-8',
		'Content-Length': str(len(sData))
	}

	# Connect to memo
	oRes = __funcToRequest[action][0](sURL, data=sData, headers=dHeaders)

	# If the request wasn't successful
	if oRes.status_code != 200:
		return {"error": {"code": 1005}}

	# Convert the result from JSON and return
	return JSON.decode(oRes.text)

def create(path, data):
	"""Create

	Make a POST request

	Arguments:
		path {str} -- The path on the service
		data {mixed} -- The data to pass to the request

	Returns:
		dict
	"""
	return __request('create', path, data)

def customerName(customerId, to_int=False, additional_fields=False):
	"""Customer Name

	Returns the first and last name of a single ID, or a dict of KNK IDs to
	names of customers for multiple IDs

	Arguments:
		customerId (uint|uint[]): A single ID or multiple IDs
		to_int (bool): Optional, if set, converts IDs to ints
		additional_fields: (False|list): Optional list of additional fields

	Returns:
		dict
	"""

	# If there's no IDs
	if not customerId:
		return {}

	# Init the data for the request
	dData = {
		"_internal_": Services.internalKey(),
		"customerId": customerId
	}

	# If additional fields are requested
	if additional_fields:
		dData['additional_fields'] = additional_fields

	# Fetch their names
	oResponse = Services.read('monolith', 'customer/name', dData)

	# If there's an error
	if oResponse.errorExists():
		raise Services.ResponseException(oResponse)

	# If there's multiple IDs
	if isinstance(customerId, list) and to_int:

		# Convert the IDs and return
		return DictHelper.keysToInts(oResponse.data)

	# Else, return as is
	return oResponse.data

def delete(path, data):
	"""Delete

	Make a DELETE request

	Arguments:
		path {str} -- The path on the service
		data {mixed} -- The data to pass to the request

	Returns:
		dict
	"""
	return __request('delete', path, data)

def name(_id):
	"""Name

	Returns the first and last name of a single ID, or a dict of memo IDs to
	names of users for multiple IDs

	Arguments:
		_id (uint|uint[]): A single ID or multiple IDs

	Returns:
		dict
	"""

	# If there's no IDs
	if not _id:
		return {}

	# Fetch their names
	oResponse = Services.read('monolith', 'user/name', {
		"_internal_": Services.internalKey(),
		"id": _id
	})

	# If there's an error
	if oResponse.errorExists():
		raise Services.ResponseException(oResponse)

	# If there's multiple IDs
	if isinstance(_id, list):

		# Convert the IDs and return
		return DictHelper.keysToInts(oResponse.data)

	# Else, return as is
	return oResponse.data

def read(path, data):
	"""Read

	Make a GET request

	Arguments:
		path {str} -- The path on the service
		data {mixed} -- The data to pass to the request

	Returns:
		dict
	"""
	return __request('read', path, data)

def update(path, data):
	"""Update

	Make a PUT request

	Arguments:
		path {str} -- The path on the service
		data {mixed} -- The data to pass to the request

	Returns:
		dict
	"""
	return __request('update', path, data)
