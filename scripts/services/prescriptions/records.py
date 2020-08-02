# coding=utf8
""" Prescriptions Records

Handles the record structures for the prescriptions service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-08-01"

# Pip imports
from FormatOC import Tree
from RestOC import Record_MySQL

# PharmacyFillError class
class PharmacyFillError(Record_MySQL.Record):
	"""PharmacyFillError

	Represents an error while attempting to fill an order with a pharmacy
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
				Tree.fromFile('../definitions/prescriptions/pharmacy_fill_error.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
