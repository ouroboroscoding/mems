# coding=utf8
""" Shared node code

Re-usable methods for nodes
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-03-08"

# Pip imports
import bottle
from RestOC import Conf, JSON, Services

def emailError(subject, error):
	"""Email Error

	Send out an email with an error message

	Arguments:
		error (str): The error to email

	Returns:
		bool
	"""

	# For debugging
	print('Emailing: %s, %s' % (subject, error))

	# Send the email
	oResponse = Services.create('communications', 'email', {
		"_internal_": Services.internalKey(),
		"text_body": error,
		"subject": subject,
		"to": Conf.get(('developer', 'emails'))
	})
	if oResponse.errorExists():
		print(oResponse.error)
		return False

	# Return OK
	return True

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

def show500():
	"""Show 500

	Display HTTP Status 500 error

	Returns:
		str
	"""
	bottle.response.status = 500
	return '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">' \
			'<html>' \
			'<head>' \
			'<title>Error: 500 Internal Server Error</title>' \
			'<style type="text/css">' \
			'html {background-color: #eee; font-family: sans;}' \
			'body {background-color: #fff; border: 1px solid #ddd;' \
			'padding: 15px; margin: 15px;}' \
			'pre {background-color: #eee; border: 1px solid #ddd; padding: 5px;}' \
			'</style>' \
			'</head>' \
			'<body>' \
			'<h1>Error: 500 Internal Server Error</h1>' \
			'<p>Sorry, the requested URL <tt>&#039;%s&#039;</tt>' \
			'caused an error:</p>' \
			'<pre>Internal Server Error</pre>' \
			'</body>' \
			'</html>' % bottle.request.url

