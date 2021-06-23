# coding=utf8
""" Konnektive Service

Handles all Konnektive requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-07-17"

# Python imports
import sys
import urllib.parse
from xml.sax.saxutils import escape

# Pip imports
import requests
import xmltodict

def address_verify(data):
	"""Address Verify

	Sends address info to USPS in order to verify it's correct. Returns
	a string describing any errors, else the properly formatted address
	based on what was provided

	Arguments:
		data (dict): Address info

	Returns:
		str|dict
	"""

	# Generate the query data
	dQuery = {
		"API": "Verify",
		"XML": '<AddressValidateRequest USERID="665MALEE6869">' \
					'<Address ID="0">' \
						'<Address1>%s</Address1><Address2>%s</Address2>' \
						'<City>%s</City><State>%s</State>' \
						'<Zip5>%s</Zip5><Zip4></Zip4>' \
					'</Address>' \
				'</AddressValidateRequest>' % (
			data['Address1'] and escape(data['Address1']) or '',
			data['Address2'] and escape(data['Address2']) or '',
			data['City'] and escape(data['City']) or '',
			data['State'] and escape(data['State']) or '',
			data['Zip5'] and escape(data['Zip5']) or ''
		)
	}

	# Send to USPS
	try:
		oRes = requests.get('https://secure.shippingapis.com/ShippingAPI.dll?%s' % urllib.parse.urlencode(dQuery))
	except ConnectionError as e:
		print('Connection error', file=sys.stderr)
		print(', '.join([str(s) for s in e.args[0]]), file=sys.stderr)
		return 'Failed to connect to USPS'

	# If the request failed
	if oRes.status_code != 200:
		print(str(oRes.status_code), file=sys.stderr)
		print(str(oRes.text), file=sys.stderr)
		return oRes.text

	# Convert the response to a dict
	dXML = xmltodict.parse(oRes.text)

	# Return the Address part
	return dXML['AddressValidateResponse']['Address']
