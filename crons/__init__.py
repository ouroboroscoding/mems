# coding=utf8
""" Crons code

Available classes/functions for running crons
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-03-29"

# Python imports
import atexit
import os
import sys

# Pip imports
from RestOC import Conf, Services

# Keep a list of running pidfiles
_lPidFiles = []

def _cleanupPidfiles():
	"""Cleanup Pidfiles

	Called when the interpreter closes

	Returns:
		None
	"""

	# Go through each pidfile and delete it
	for s in _lPidFiles:
		os.unlink(s)

# Register at exit function
atexit.register(_cleanupPidfiles)

def emailError(subject, error, recipient=None):
	"""Email Error

	Send out an email with an error message

	Arguments:
		subject (str): The subject of the email
		error (str): The error to email
		recipient (str|str[]): The recipient of the email

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
		"to": recipient or Conf.get(('developer', 'emails'))
	})
	if oResponse.errorExists():
		print(oResponse.error)
		return False

	# Return OK
	return True

def isRunning(name):
	"""Is Running

	Checks if the cron job is already running, if not, creates pidfile so
	future calls return true

	Arguments:
		name {str} -- The name of the cron job to check

	Returns:
		bool
	"""

	# Import pidfile list
	global _lPidFiles

	# Generate the nameof the files
	sFile = '/tmp/%s.pid' % name

	# If the file already exists
	if os.path.isfile(sFile):
		return True

	# Create the file, write to, and close the file
	oFile = open(sFile, 'w')
	oFile.write(str(os.getpid()))
	oFile.close()

	# Add the file to the pidfiles
	_lPidFiles.append(sFile)

	# Return was not running
	return False
