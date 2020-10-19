# coding=utf8
""" Customers Records

Handles the record structures for the Customers service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-08-18"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# Shared imports
from shared import Record_MySQLSearch

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
class Customer(Record_MySQLSearch.Record):
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
			cls._conf = Record_MySQLSearch.Record.generateConfig(
				Tree.fromFile('definitions/customers/customer.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

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
