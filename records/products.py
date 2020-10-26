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
	def allByGroup(cls, custom={}):
		"""All By Groun

		Returns all products available by group and name

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT `p`.`*`,\n" \
				"	`g`.`name` as `group_name`,\n" \
				"	`m`.`name` as `medication_name`\n" \
				"FROM `%(db)s`.`%(table)s` as `p`\n" \
				"JOIN `%(db)s`.`products_group` as `g` ON `g`.`_id` = `p`.`group`\n" \
				"INNER JOIN `%(db)s`.`products_medication` as `m` ON `m`.`_id` = `p`.`medication`\n" \
				"ORDER BY `group_name`, `name`" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Select all the records
		lRows = Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL
		)

		# Return the records
		return lRows

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
