# coding=utf8
""" Qualified Medication Records

Handles the record structures for the Qualified Medication service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-10-12"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# Item class
class Item(Record_MySQL.Record):
	"""Item

	Represents a single qualified medication for a customer
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
				Tree.fromFile('definitions/qualmed/item.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
