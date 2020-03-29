# coding=utf8
""" Upgrades code

Available classes/functions for running upgrades
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-03-29"

# Python imports
from time import time

# Project imports
from shared import JSON

class UpgradeLog(object):
	"""Upgrade Log

	Class to manage an upgrade log file

	Extends:
		object
	"""

	def __init__(self, _file):
		"""Constructor

		Initialises the instance

		Args:
			_file (str): The path to the upgrade log file

		Returns:
			UpgradeLog
		"""

		# Store the filename
		self.__file = _file

		# Try to open the file
		try:
			self.__log = JSON.load(self.__file)

		# If the file doesn't exist
		except IOError:

			# Set an empty log
			self.__log = {}

			# Make sure we can store the log before we continue
			#	don't catch any exceptions so that they bubble up
			JSON.store(self.__log, self.__file)

	def __contains__(self, module):
		"""__contains__

		Returns true if the specific key exists in the session

		Args:
			module (str): The name of the module to check for

		Returns:
			bool
		"""
		return module in self.__log

	# __getitem__ method
	def __getitem__(self, module):
		"""__getitem__

		Returns a specific key from the dict

		Args:
			module (str): The name of the module to return

		Returns:
			mixed
		"""
		return self.__log[module]

	# __iter__ method
	def __iter__(self):
		"""__iter__

		Return an iterator for the modules

		Returns:
			iterator
		"""
		return iter(self.__log)

	# __setitem__ method
	def __setitem__(self, module, ts):
		"""Set Item (__setitem__)

		Sets a specific key in the dict

		Args:
			module (str): The module to set
			ts (uint): The timestamp it was run

		Returns:
			None
		"""

		# Set the timestamp for the module
		self.__log[module] = ts

		# Store the updated log
		JSON.store(self.__log, self.__file)

	# __str__ method
	def __str__(self):
		"""__str__

		Returns a string representation of the modules

		Returns:
			str
		"""
		return str(self.__log)

def run(l, log):
	"""Run

	Is given a list of modules to run and stores their successful times

	Arguments:
		l {list} -- A list of modules to run
		log {UpgradeLog} -- The log file to store times in

	Returns:
		bool
	"""

	# Go through each module in order
	for m in l:

		# If we already ran the module
		if m.__name__ in log:

			# Skip it
			print('Skipping %s' % m.__name__)
			continue

		# Run the upgrade module
		print('Running %s' % m.__name__)
		res = False
		try:
			res = m.run()
		except Exception as e:
			print("%s\n" % str(e))

		# If we failed
		if not res:
			print('Failed to run %s\nQuitting\n' % m.__name__)
			return False

		# Else update the log
		log[m.__name__] = int(time())

	# Return OK
	return True
