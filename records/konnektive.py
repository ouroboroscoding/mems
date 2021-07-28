# coding=utf8
""" Konnektive Records

Handles the record structures for the Konnektive service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2021-07-22"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, JSON, Record_MySQL

# Campaign class
class Campaign(Record_MySQL.Record):
	"""Campaign

	Represents a campaign in Konnektive
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
				Tree.fromFile('definitions/konnektive/campaign.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# CampaignProduct class
class CampaignProduct(Record_MySQL.Record):
	"""Campaign Product

	Represents a product in a specific campaign in Konnektive
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
				Tree.fromFile('definitions/konnektive/campaign_product.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
