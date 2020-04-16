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

# Merchant structure and config
_mdMerchantConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/payments/merchant.json'),
	'mysql'
)

# VaultCustomer structure and config
_mdVaultCustomerConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/payments/vault_customer.json'),
	'mysql'
)

# Merchant class
class Merchant(Record_MySQL.Record):
	"""Merchant

	Represents a MID

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdMerchantConf

# VaultCustomer class
class VaultCustomer(Record_MySQL.Record):
	"""VaultCustomer

	Represents an customer in a gateway vault

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdVaultCustomerConf
