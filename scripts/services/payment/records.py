# coding=utf8
""" Payment Records

Handles the record structures for the payments service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-04-08"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# Customer class
class Customer(Record_MySQL.Record):
	"""Customer

	Represents a customer for the sake of rebilling/upselling
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
				Tree.fromFile('../definitions/payment/customer.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
