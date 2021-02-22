# coding=utf8
""" Environment

Shared functionality to deal with environment data
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-12-14"

def getClientIP(environ):
	"""Get Client IP

	Returns the IP of the client when connecting via webserver

	Returns:
		str
	"""

	# Init return var
	sIP	= '0.0.0.0'

	# Check common environment variables
	if 'HTTP_CLIENT_IP' in environ:
		sIP = environ['HTTP_CLIENT_IP']
	elif 'HTTP_X_CLIENTIP' in environ:
		sIP = environ['HTTP_X_CLIENTIP']
	elif 'HTTP_X_FORWARDED_FOR' in environ:
		sIP = environ['HTTP_X_FORWARDED_FOR']
	elif 'HTTP_X_RN_XFF' in environ:
		sIP = environ['HTTP_X_RN_XFF']
	elif 'REMOTE_ADDR' in environ:
		sIP = environ['REMOTE_ADDR']

	# If there's multiple IPs
	if sIP.find(','):
		lIPs = sIP.split(',')
		sIP = lIPs[-1].strip()

	# Return the IP
	return sIP
