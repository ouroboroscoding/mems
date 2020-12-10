# coding=utf8
""" Providers Records

Handles the record structures for the Providers service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-10-15"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# ProductToRx class
class ProductToRx(Record_MySQL.Record):
	"""ProductToRx

	Represents a single order item and its prescription in DoseSpot
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
				Tree.fromFile('definitions/providers/product_to_rx.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def updateCustomer(cls, customer_id, products, user_id, custom={}):
		"""Update Customer

		Create/Update multiple products associated with a customer

		Arguments:
			customer_id (uint): The ID of the customer
			products (dict[]) : List of product and dosespot IDs
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Create each insert
		lInserts = []
		for d in products:
			lInserts.append('(%d, %d, %d, %d)' % (
				customer_id,
				d['product_id'],
				d['ds_id'],
				user_id
			))

		# Generate SQL
		sSQL = 'INSERT INTO `%(db)s`.`%(table)s` ' \
				'(`customer_id`, `product_id`, `ds_id`, `user_id`)\n' \
				'VALUES %(inserts)s\n' \
				'ON DUPLICATE KEY UPDATE `ds_id` = VALUES(`ds_id`)' % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"inserts": ',\n'.join(lInserts)
		}

		# Insert the record
		Record_MySQL.Commands.execute(
			dStruct['host'],
			sSQL
		)

# Provider class
class Provider(Record_MySQL.Record):
	"""Provider

	Represents a memo user in mems
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
				Tree.fromFile('definitions/providers/provider.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# RoundRobinAgent class
class RoundRobinAgent(Record_MySQL.Record):
	"""RoundRobinAgent

	Represents a single order item and its prescription in DoseSpot
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
				Tree.fromFile('definitions/providers/round_robin_agent.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Template class
class Template(Record_MySQL.Record):
	"""Template

	Represents an note/sms template
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
				Tree.fromFile('definitions/providers/template.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Tracking class
class Tracking(Record_MySQL.Record):
	"""Tracking

	Represents tracking of providers and their actions
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
				Tree.fromFile('definitions/providers/tracking.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
