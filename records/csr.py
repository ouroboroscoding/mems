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

# Action class
class Action(Record_MySQL.Record):
	""" Action

	Represents an action taken
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
				Tree.fromFile('definitions/csr/action.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def agentCounts(cls, range_, memo_ids=None, custom={}):
		"""Agent Counts

		Returns the count per type of outgoing item by agent

		Arguments:
			range_ (list): The timestamp start and end to look up
			memo_ids (list): Optional, the list of agents to look for
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT `memo_id`, `type`, COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `_created` BETWEEN FROM_UNIXTIME(%(start)d) AND FROM_UNIXTIME(%(end)d)\n" \
				"%(memo_id)s" \
				"GROUP BY `memo_id`, `type`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"start": range_[0],
			"end": range_[1],
			"memo_id": memo_ids and ('AND `memo_id` IN (%s)\n' % ','.join([str(s) for s in memo_ids])) or ''
		}

		# Return the counts
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	@classmethod
	def byRange(cls, start, end, memo_id=None, custom={}):
		"""By Range

		Returns the actions in the given date/time range and single or group of
		agents

		Arguments:
			start (uint): The start timestamp of the range
			end (uint): The end timestamp of the range
			memo_id (int): The ID of the memo user to fetch tickets for

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the where clauses
		sWhere = '`_created` BETWEEN FROM_UNIXTIME(%d) AND FROM_UNIXTIME(%d)' % (
			start, end
		)
		if memo_id:
			if isinstance(memo_id, list):
				sWhere += '\nAND `memo_id` IN (%s)' % ','.join([str(s) for s in memo_id])
			else:
				sWhere += '\nAND `memo_id` = %d' % memo_id

		# Generate the SQL
		sSQL = "SELECT *\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE %(where)s\n" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"where": sWhere
		}

		# Fetch and return the records
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

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

	@classmethod
	def memoIdsByType(cls, type_, custom={}):
		"""Memo IDs by Type

		Returns the memo IDs of all agents with the given type set

		Arguments:
			type_ (str): The type to return IDs for
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			uint[]
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT `memo_id`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `type` REGEXP '\\\\b%(type)s\\\\b'" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"type": type_
		}

		# Delete all the records
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.COLUMN
		)

# AgentOfficeHours class
class AgentOfficeHours(Record_MySQL.Record):
	"""Agent Office Hours

	Represents the hours an agent is in the office during a specific day of the
	week
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
				Tree.fromFile('definitions/csr/agent_office_hours.json'),
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

# Lead class
class Lead(Record_MySQL.Record):
	""" Lead

	Represents a possible customer upsell lead
	"""

	MEDICATION_ED	= 0x01
	MEDICATION_HRT	= 0x02
	"""Defines"""

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
				Tree.fromFile('definitions/csr/lead.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

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

	Represents a support ticket
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
				Tree.fromFile('definitions/csr/ticket.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def withState(cls, ids=None, custom={}):
		"""With State

		Returns tickets with their associated opened and resolved records based
		on the given IDs. To first get IDs take a look at the idsByRange method

		Arguments:
			ids (str[]): List of IDs to return
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT\n" \
				"	`t`.*,\n" \
				"	`o`.`_created` as `opened_ts`,\n" \
				"	`o`.`type` as `opened_type`,\n" \
				"	`o`.`memo_id` as `opened_user`,\n" \
				"	`r`.`_created` as `resolved_ts`,\n" \
				"	`r`.`type` as `resolved_type`,\n" \
				"	`r`.`memo_id` as `resolved_user`\n" \
				"FROM `%(db)s`.`%(table)s` as `t`\n" \
				"JOIN `%(db)s`.`%(table)s_opened` as `o` ON\n" \
				"	`t`.`_id` = `o`.`_ticket`\n" \
				"LEFT JOIN `%(db)s`.`%(table)s_resolved` as `r` ON\n" \
				"	`t`.`_id` = `r`.`_ticket`\n" \
				"WHERE `t`.`_id` IN ('%(ids)s')\n" \
				"ORDER BY `o`.`_created`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"ids": "','".join(ids)
		}

		# Delete all the records
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	@classmethod
	def unresolved(cls, filter, custom={}):
		"""Unresolved

		Returns the ID if any ticket is found not yet resolved based on the
		filter

		Arguments:
			filter (dict): The filter to use for the lookup
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			str|None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Go through each value
		lWhere = [];
		for n,v in filter.items():

			# Generate theSQL and append it to the list
			lWhere.append(
				'`%s` %s' % (n, cls.processValue(dStruct, n, v))
			)

		# Generate the SQL
		sSQL = "SELECT `t`.`_id`\n" \
				"FROM `%(db)s`.`%(table)s` as `t`\n" \
				"LEFT JOIN `%(db)s`.`%(table)s_resolved` as `r` ON\n" \
				"	`t`.`_id` = `r`.`_ticket`\n" \
				"WHERE `r`.`type` is NULL\n" \
				"AND %(where)s" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"where": ' AND '.join(lWhere)
		}

		# Delete all the records
		Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.CELL
		)

	@classmethod
	def idsByRange(cls, start, end, memo_id=None, custom={}):
		"""User Associated

		Combines the opened, resolved, and actions tables into a single
		union and returns the distinct ticket IDs found to be associated in
		the given date/time range

		Arguments:
			start (uint): The start timestamp of the range
			end (uint): The end timestamp of the range
			memo_id (int): The ID of the memo user to fetch tickets for

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the where clauses
		sWhere = '`_created` BETWEEN FROM_UNIXTIME(%d) AND FROM_UNIXTIME(%d)' % (
			start, end
		)
		if memo_id:
			if isinstance(memo_id, list):
				sWhere += '\nAND `memo_id` IN (%s)' % ','.join([str(s) for s in memo_id])
			else:
				sWhere += '\nAND `memo_id` = %d' % memo_id

		# Generate the SQL
		sSQL = "SELECT `_ticket` as `ticket`\n" \
				"FROM `%(db)s`.`%(table)s_opened`\n" \
				"WHERE %(where)s\n" \
				"UNION\n" \
				"SELECT `_ticket` as `ticket`\n" \
				"FROM `%(db)s`.`%(table)s_resolved`\n" \
				"WHERE %(where)s\n" \
				"UNION\n" \
				"SELECT DISTINCT `ticket`\n" \
				"FROM `%(db)s`.`%(table)s_action`\n" \
				"WHERE %(where)s\n" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"where": sWhere
		}

		# Get the ticket IDs
		lIDs = Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.COLUMN
		)

		# If we have any
		if lIDs:
			lIDs = list(set(lIDs))

		# Return the IDs
		return lIDs

# TicketAction class
class TicketAction(Record_MySQL.Record):
	"""Ticket Action

	Represents an action taken on a support ticket
	"""

	_conf = None
	"""Configuration"""

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

	@classmethod
	def typeText(cls, name, type_):
		"""Type Text

		Returns the text representation of the action type

		Arguments:
			name (str): The action name
			type (uint): The action type

		Returns:
			str
		"""
		if name not in cls.types or type_ not in cls.types[name]:
			return 'MISSING'
		else:
			return cls.types[name][type_]

# TicketItem class
class TicketItem(Record_MySQL.Record):
	"""Ticket Item

	Represents an item attached to a support ticket
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def addSMS(cls, ticket, ids, custom={}):
		"""Add SMS

		Adds a list of SMS ids while ignoring any duplicates

		Arguments:
			ticket (str): The ID of the ticket
			ids (list): The IDs to add as items
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the values
		lValues = [
			"(UUID(), '%s', 'sms', 'incoming', '%s', 0)" % (ticket, s)
			for s in ids
		]

		# Generate the SQL
		sSQL = 'INSERT IGNORE INTO `%(db)s`.`%(table)s` (`_id`, `ticket`, `type`, `direction`, `identifier`, `memo_id`) VALUES\n' \
				'%(inserts)s' % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"inserts": ',\n'.join(lValues)
		}

		# Execute the inserts
		Record_MySQL.Commands.execute(
			dStruct['host'],
			sSQL
		)

	@classmethod
	def agentCounts(cls, range_, memo_ids=None, custom={}):
		"""Agent Counts

		Returns the count per type of outgoing item by agent

		Arguments:
			range_ (list): The timestamp start and end to look up
			memo_ids (list): Optional, the list of agents to look for
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT `memo_id`, `type`, COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `_created` BETWEEN FROM_UNIXTIME(%(start)d) AND FROM_UNIXTIME(%(end)d)\n" \
				"AND (\n" \
				"	(`type` IN ('sms', 'note') AND `direction` = 'outgoing') OR\n" \
				"	`type` IN ('jc_call', 'order')\n" \
				")\n" \
				"%(memo_id)s" \
				"GROUP BY `memo_id`, `type`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"start": range_[0],
			"end": range_[1],
			"memo_id": memo_ids and ('AND `memo_id` IN (%s)\n' % ','.join([str(s) for s in memo_ids])) or ''
		}

		# Return the counts
		return Record_MySQL.Commands.select(
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

# TicketOpened class
class TicketOpened(Record_MySQL.Record):
	"""Ticket Opened

	Represents when a support ticket was opened
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def agentCounts(cls, range_, memo_ids=None, custom={}):
		"""Agent Counts

		Returns the count per type of opened ticket by agent

		Arguments:
			range_ (list): The timestamp start and end to look up
			memo_ids (list): Optional, the list of agents to look for
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the WHERE
		lWhere = ['`_created` BETWEEN FROM_UNIXTIME(%d) AND FROM_UNIXTIME(%d)' % (
			range_[0], range_[1]
		)]
		if memo_ids:
			lWhere.append('`memo_id` IN (%s)' % ','.join([str(s) for s in memo_ids]))

		# Generate the SQL
		sSQL = "SELECT `memo_id`, `type`, COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE %(where)s\n" \
				"GROUP BY `memo_id`, `type`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"where": '\nAND '.join(lWhere)
		}

		# Return the counts
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	@classmethod
	def countByUser(cls, memo_id, range_=None, custom={}):
		"""Count By User

		Returns the total count of opened tickets by a specific user, with or
		without a specific range

		Arguments:
			memo_id (uint): The ID of the user
			range_ (list): Optional range to filter by, 0 = start, 1 = end
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			uint
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Init where
		lWhere = ['`memo_id` = %d' % memo_id]

		# If we have a range
		if range_:
			lWhere.append('`_created` BETWEEN FROM_UNIXTIME(%d) AND FROM_UNIXTIME(%d)' % (
				range_[0], range_[1]
			))

		# Generate the SQL
		sSQL = "SELECT COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE %(where)s" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"where": '\nAND '.join(lWhere)
		}

		# Return the count
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.CELL
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
				Tree.fromFile('definitions/csr/ticket_opened.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def counts(cls, start, end, custom={}):
		"""Counts

		Returns the counts group by the users

		Arguments:
			start (int): The starting timestamp
			end (int): The ending timestamp
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			uint
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT `memo_id`, COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `_created` BETWEEN FROM_UNIXTIME(%(start)d) AND FROM_UNIXTIME(%(end)d)\n" \
				"GROUP BY `memo_id`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"start": start,
			"end": end
		}

		# Return all the records
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# TicketResolved class
class TicketResolved(Record_MySQL.Record):
	"""Ticket Resolved

	Represents when a support ticket was resolved
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def agentCounts(cls, range_, memo_ids=None, custom={}):
		"""Agent Counts

		Returns the count per type of opened ticket by agent

		Arguments:
			range_ (list): The timestamp start and end to look up
			memo_ids (list): Optional, the list of agents to look for
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the WHERE
		lWhere = ['`_created` BETWEEN FROM_UNIXTIME(%d) AND FROM_UNIXTIME(%d)' % (
			range_[0], range_[1]
		)]
		if memo_ids:
			lWhere.append('`memo_id` IN (%s)' % ','.join([str(s) for s in memo_ids]))

		# Generate the SQL
		sSQL = "SELECT `memo_id`, `type`, COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE %(where)s\n" \
				"GROUP BY `memo_id`, `type`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"where": '\nAND '.join(lWhere)
		}

		# Return the counts
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	@classmethod
	def countByUser(cls, memo_id, range_=None, custom={}):
		"""Count By User

		Returns the total count of opened tickets by a specific user, with or
		without a specific range

		Arguments:
			memo_id (uint): The ID of the user
			range_ (list): Optional range to filter by, 0 = start, 1 = end
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			uint
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Init where
		lWhere = ['`memo_id` = %d' % memo_id]

		# If we have a range
		if range_:
			lWhere.append('`_created` BETWEEN FROM_UNIXTIME(%d) AND FROM_UNIXTIME(%d)' % (
				range_[0], range_[1]
			))

		# Generate the SQL
		sSQL = "SELECT COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE %(where)s" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"where": '\nAND '.join(lWhere)
		}

		# Return the count
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.CELL
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
				Tree.fromFile('definitions/csr/ticket_resolved.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def counts(cls, start, end, custom={}):
		"""Counts

		Returns the counts group by the users

		Arguments:
			start (int): The starting timestamp
			end (int): The ending timestamp
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			uint
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT `memo_id`, COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `_created` BETWEEN FROM_UNIXTIME(%(start)d) AND FROM_UNIXTIME(%(end)d)\n" \
				"GROUP BY `memo_id`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"start": start,
			"end": end
		}

		# Return all the records
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# TicketStat class
class TicketStat(Record_MySQL.Record):
	"""Ticket Stat

	Represents a single state by day/week/month for a user or group of users
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
				Tree.fromFile('definitions/csr/ticket_stat.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
