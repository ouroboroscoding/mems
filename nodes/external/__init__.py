# coding=utf8
""" External Node

Re-usable methods for external
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-12-06"

# Pip imports
import bottle
from RestOC import JSON

def reqJSON():
	"""Request Body

	Decodes the JSON body and returns it

	Returns:
		mixed
	"""
	try: sBody = bottle.request.body.getvalue()
	except AttributeError as e: sBody = bottle.request.body.read()
	return JSON.decode(sBody)

def resJSON(val):
	"""Response JSON

	Encodes value as JSON and returns it

	Arguments:
		val (mixed): The data to encode and return

	Returns:
		str
	"""
	bottle.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
	return JSON.encode(val);
