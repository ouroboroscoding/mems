# coding=utf8
""" Docs Records

Handles the record structures for the Docs service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2021-02-06"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, JSON, Record_MySQL

# ErrorRecord class
class ErrorRecord(Record_MySQL.Record):
	"""Error Record

	Represents a possible error in the API
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
				Tree.fromFile('definitions/docs/error.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# NounRecord class
class NounRecord(Record_MySQL.Record):
	"""Noun Record

	Represents a noun in a service
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
				Tree.fromFile('definitions/docs/noun.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# ServiceRecord class
class ServiceRecord(Record_MySQL.Record):
	"""Service Record

	Represents a service
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
				Tree.fromFile('definitions/docs/service.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
