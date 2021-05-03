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
from RestOC import Conf, DictHelper, JSON, Record_MySQL

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

# Ticket class
class Ticket(Record_MySQL.Record):
	"""Ticket

	Represents an support ticket
	"""

	_conf = None
	"""Configuration"""

	_resolved = None
	"""Holds the unsigned integer representing resolved"""

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
				Tree.fromFile('definitions/csr/ticket.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def withResolution(ids=None, between=None):
		"""With Resolutions

		Returns tickets with their associated resolutions, even if not resolved
		yet

		Arguments:
			ids (str[]): Optional list of IDs to return
			between (list): Optional range of tickets 0 => start, 1 => end

		Returns:
			list
		"""

		# Init the WHERE
		lWhere = []

		# If we have IDs
		if ids:
			lWhere.append("`t`.`_id` IN ('%s')" % "','".join(ids))

		# If we have a range
		if between:
			lWhere.append("`t`.`resolved` BETWEEN FROM_UNIXTIME(%d) AND FROM_UNIXTIME(%d)" % (
				between[0], between[1]
			))

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT\n" \
				"	`t`.*,\n" \
				"	`a`.`memo_id`,\n" \
				"	`a`.`subtype`\n" \
				"FROM `%(db)s`.`%(table)s` as `t`\n" \
				"LEFT JOIN `%(db)s`.`ticket_action` as `a` ON (\n" \
				"	`t`.`_id` = `a`.`ticket` AND\n" \
				"	`a`.`type` = %(resolved)d\n" \
				")\n" \
				"WHERE %s\n" \
				"ORDER BY `_created`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"list": list_id,
			"resolved": TicketAction.resolved()
		}

		# Delete all the records
		Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# TicketAction class
class TicketAction(Record_MySQL.Record):
	"""Ticket Action

	Represents an action taken on a support ticket
	"""

	_conf = None
	"""Configuration"""

	_resolved = None
	"""The unsigned integer used to represent 'Resolved'"""

	subtypes = None
	"""The allowed subtypes of actions based on the type"""

	types = None
	"""The allowed types of actions"""

	@classmethod
	def byTicket(cls, ticket, custom={}):
		"""By Ticket

		Return all actions associated with a specific ticket ID

		Arguments:
			ticket (str): The ID of the ticket
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT *\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `ticket` = '%(ticket)s'" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"ticket": ticket
		}

		# Delete all the records
		Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

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
				Tree.fromFile('definitions/csr/ticket_action.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def init(cls):
		"""Init

		Initialises the class so necessary data is loaded

		Returns:
			None
		"""

		# Load the ticket action types and subtypes
		cls.types = DictHelper.keysToInts(
			JSON.load('definitions/csr/ticket_action_types.json')
		)
		cls.subtypes = DictHelper.keysToInts(
			JSON.load('definitions/csr/ticket_action_subtypes.json')
		)

		# Go through each acton type
		for i,s in cls.types.items():

			# If the string is resolved
			if s == 'Resolved':

				# Set the value in the table
				cls._resolved = i
				break

	@classmethod
	def resolved(cls):
		"""Resolved

		Returns the resolved ID

		Returns:
			uint
		"""
		return cls._resolved

# TicketItem class
class TicketItem(Record_MySQL.Record):
	"""Ticket Item

	Represents an item attached to a support ticket
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def byTicket(cls, ticket, custom={}):
		"""By Ticket

		Return all items associated with a specific ticket ID

		Arguments:
			ticket (str): The ID of the ticket
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT *\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `ticket` = '%(ticket)s'" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"ticket": ticket
		}

		# Delete all the records
		Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

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
				Tree.fromFile('definitions/csr/ticket_item.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
