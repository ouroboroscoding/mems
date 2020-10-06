# coding=utf8
""" Products Records

Handles the record structures for the Products service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-10-06"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# Group class
class Group(Record_MySQL.Record):
	"""Group

	Represents a single product group in the system
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
				Tree.fromFile('definitions/products/group.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Medication class
class Medication(Record_MySQL.Record):
	"""Medication

	Represents a single product medication in the system
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
				Tree.fromFile('definitions/products/medication.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Product class
class Product(Record_MySQL.Record):
	"""Product

	Represents a single product in the system
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
				Tree.fromFile('definitions/products/product.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
