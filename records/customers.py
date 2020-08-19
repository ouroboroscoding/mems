# coding=utf8
""" Customers Records

Handles the record structures for the Customers service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-10-18"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# Address class
class Address(Record_MySQL.Record):
	"""Address

	Represents a single address associated with a customer
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""

		# If we haven loaded the config yet
		if not cls._conf:
			cls._conf = Record_MySQL.Record.generateConfig(
				Tree.fromFile('definitions/customers/address.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Customer class
class Customer(Record_MySQL.Record):
	"""Customer

	Represents a single customer
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""

		# If we haven loaded the config yet
		if not cls._conf:
			cls._conf = Record_MySQL.Record.generateConfig(
				Tree.fromFile('definitions/customers/customer.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def search(cls, filter, custom={}):
		"""Search

		Does a text based LIKE search for customers rather than checking if
		values are exactly as sent

		Arguments:
			filter (dict): Lists of fields to search against
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict[]
		"""
		pass

# Note class
class Note(Record_MySQL.Record):
	"""Note

	Represents a single note associated with a customer
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""

		# If we haven loaded the config yet
		if not cls._conf:
			cls._conf = Record_MySQL.Record.generateConfig(
				Tree.fromFile('definitions/customers/note.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
