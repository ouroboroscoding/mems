# coding=utf8
""" CSR Records

Handles the record structures for the CSR service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-05-17"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# Agent class
class Agent(Record_MySQL.Record):
	"""Agent

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
				Tree.fromFile('definitions/csr/agent.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# CustomList class
class CustomList(Record_MySQL.Record):
	"""CustomList

	Represents a custom list by a CSR agent
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
				Tree.fromFile('definitions/csr/custom_list.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# CustomListItem class
class CustomListItem(Record_MySQL.Record):
	"""CustomListItem

	Represents a single item in a custom list
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
				Tree.fromFile('definitions/csr/custom_list_item.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def deleteByList(cls, list_id, custom={}):
		"""Delete By List

		Removes all recrods associated with a specific list

		Arguments:
			list_id (str): The ID of the list to delete items from
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "DELETE FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `list` = '%(list)s'" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"list": list_id
		}

		# Delete all the records
		Record_MySQL.Commands.execute(
			dStruct['host'],
			sSQL
		)

# Reminder class
class Reminder(Record_MySQL.Record):
	"""Reminder

	Represents a reminder for an agent
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
				Tree.fromFile('definitions/csr/reminder.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# TemplateEmail class
class TemplateEmail(Record_MySQL.Record):
	"""TemplateEmail

	Represents an email template
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
				Tree.fromFile('definitions/csr/tpl_email.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# TemplateSMS class
class TemplateSMS(Record_MySQL.Record):
	"""TemplateSMS

	Represents an SMS template
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
				Tree.fromFile('definitions/csr/tpl_sms.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
