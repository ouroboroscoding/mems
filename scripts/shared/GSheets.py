# coding=utf8
""" GSheets

Shared functionality to deal with parsing / writing Google Sheets
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-08-10"

# Python imports
from time import sleep

# Pip imports
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from RestOC import Conf

_auth = {}
"""Clients for re-use"""

_files = {}
"""Files for re-use"""

def _authorize(name):
	"""Authorize

	Authorizes the oauth2 credentials for communicating with google

	Arguments:
		name (str): The name of the auth so we can get the config

	Returns:
		gspread.client
	"""

	# If we don't have the client
	if name not in _auth:

		# Get the name of the file
		sFile = Conf.get(('google', 'sheets', name))

		# Use credentials to interact with the Google Drive API
		oCreds = ServiceAccountCredentials.from_json_keyfile_name(
					sFile,
					['https://spreadsheets.google.com/feeds',
						'https://www.googleapis.com/auth/drive']
				)

		# Create the client
		_auth[name] = gspread.authorize(oCreds)

	# Return the client
	return _auth[name]

def _open_file(auth, key):
	"""Open File

	Creates a file pointer for the give key

	Arguments:
		auth (str): The name of the auth to use to open the file
		key (str): The file's unique key

	Returns:
		gspread.models.Spreadsheet
	"""

	# If we don't have the file
	if key not in _files:

		# Get the auth
		oClient = _authorize(auth)

		# Open the file
		_files[key] = oClient.open_by_key(key)

	# Return the model
	return _files[key]

def insert(auth, key, worksheet, data, row, method='USER_ENTERED'):
	"""Insert

	Inserts a row into the worksheet

	Arguments:
		auth (str): The auth to use to open the file
		key (str): The key associated with the file
		worksheet (str): The worksheet within the file to write to
		data (list): The list of data to write to the row
		row (uint): The row to insert at
		method (str): The method to use to write the row

	Returns:
		None
	"""

	# Loop in case we lose the authorization
	while True:
		try:

			# Get the file model
			oFile = _open_file(auth, key)

			# Write the data
			oFile.worksheet(worksheet).insert_row(
				data, row, method
			)

			# Sleep for as many seconds as there is columns in the data
			sleep(len(data))

			# Return OK
			return

		# If there's any error, clear the auth and file and try again
		except gspread.exceptions.APIError:
			try: del _auth[auth]
			except KeyError: pass
			try: del _file[key]
			except KeyError: pass
			continue
