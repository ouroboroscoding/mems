# coding=utf8
""" Services code

Available classes/functions for running services
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-09-29"

# Pip imports
from RestOC import Conf, Services

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
