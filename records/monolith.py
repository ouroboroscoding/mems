# coding=utf8
""" Monolith Records

Handles the record structures for the monolith service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-04-26"

# Python imports
import copy
from hashlib import sha1
import re
from time import time

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# Custome SQL
sConversationSQL = ''
sLatestStatusSQL = ''
sSmpNotes = ''
sSmpNotesNew = ''
sNumOfOrdersSQL = ''
sSearchSQL = ''

def init():
	"""Ugly Hack

	Need to find a better way to do this
	"""

	global sConversationSQL, sLatestStatusSQL, sSmpNotes, sSmpNotesNew, \
			sNumOfOrdersSQL, sSearchSQL

	# SQL files
	with open('records/sql/conversation.sql') as oF:
		sConversationSQL = oF.read()
	with open('records/sql/latest_status.sql') as oF:
		sLatestStatusSQL = oF.read()
	with open('records/sql/smp_notes.sql') as oF:
		sSmpNotes = oF.read()
	with open('records/sql/smp_notes_new.sql') as oF:
		sSmpNotesNew = oF.read()
	with open('records/sql/number_of_orders.sql') as oF:
		sNumOfOrdersSQL = oF.read()
	with open('records/sql/search.sql') as oF:
		sSearchSQL = oF.read()

# Calendly class
class Calendly(Record_MySQL.Record):
	"""Calendly

	Represents a customer conversation that has been claimed by an agent
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
				Tree.fromFile('definitions/monolith/calendly.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def byCustomer(cls, customer_id, custom={}):
		"""By Customer

		Searches calendly appointments by joining with KtCustomer and comparing
		phone number or email

		Arguments:
			customer_id (int): The unique ID of the customer
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT `cal`.`prov_name`, `cal`.`prov_emailAddress`, " \
				"`cal`.`start`, `cal`.`end`\n" \
				"FROM `%(db)s`.`%(table)s` as `cal`,\n" \
				"	`%(db)s`.`kt_customer` as `ktc`\n" \
				"WHERE `ktc`.`customerId` = '%(id)d'\n" \
				"AND (\n" \
				"	`ktc`.`phoneNumber` = `cal`.`pat_phoneNumber` OR\n" \
				"	`ktc`.`emailAddress` = `cal`.`pat_emailAddress`\n" \
				")" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"id": customer_id
		}

		# Execute and return the select
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# Campaign class
class Campaign(Record_MySQL.Record):
	"""Campaign

	Represents a campaign in KNK and the type associated
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
				Tree.fromFile('definitions/monolith/campaign.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def ids(cls, custom={}):
		"""IDs

		Returns the set of campaign IDs

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT `id`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"ORDER BY `id`" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Return the IDs as a list
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.COLUMN
		)

# CustomerClaimed class
class CustomerClaimed(Record_MySQL.Record):
	"""CustomerClaimed

	Represents a customer conversation that has been claimed by an agent
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
				Tree.fromFile('definitions/monolith/customer_claimed.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def counts(cls, ids=None, custom={}):
		"""Counts

		Returns the count of claims per user

		Arguments:
			ids (int[]): List of IDs to look for
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# If we have IDs
		sWhere = ids and ('WHERE `user` in (%s)\n' % ','.join(ids)) or ''

		# Generate SQL
		sSQL = "SELECT `user`, COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"%(where)s" \
				"GROUP BY `user`\n" \
				"ORDER BY `count` ASC" % {
					"db": dStruct['db'],
					"table": dStruct['table'],
					"where": sWhere
				}

		# Fetch the data and return the records
		return Record_MySQL.Commands.select(dStruct['host'], sSQL)

	@classmethod
	def stats(cls, custom={}):
		"""Stats

		Returns stats of claims by user

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT CONCAT(`u`.`lastName`, ', ', `u`.`firstName`) as `name`, COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s` as `cc`, `%(db)s`.`user` as `u`\n" \
				"WHERE `cc`.`user` = `u`.`id`\n" \
				"GROUP BY `u`.`id`\n" \
				"ORDER BY `name`" % {
					"db": dStruct['db'],
					"table": dStruct['table']
				}

		# Fetch the data and return the records
		return Record_MySQL.Commands.select(dStruct['host'], sSQL)

# CustomerClaimedLast class
class CustomerClaimedLast(Record_MySQL.Record):
	"""CustomerClaimedLast

	Represents the last time a user looked up new messages on claimed
	conversations
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
				Tree.fromFile('definitions/monolith/customer_claimed_last.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def get(cls, user, custom={}):
		"""Get

		Get's the last timestamp for the given user

		Arguments:
			user (uint): The user to get the timestamp for
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			uint
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = 'SELECT UNIX_TIMESTAMP(`timestamp`)\n' \
			'FROM `%(db)s`.`%(table)s`\n' \
			'WHERE `user` = %(user)d' % {
				"db": dStruct['db'],
				"table": dStruct['table'],
				"user": user
			}

		# Fetch the value
		iTS = Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.CELL
		)

		# If we got no value
		if not iTS:
			iTS = int(time())

		# Return the timestamp
		return iTS

	@classmethod
	def set(cls, user, ts, custom={}):
		"""Set

		Updates the current value for the user or else creates it

		Arguments:
			user (uint): The unique ID of the user the timestamp is
				associated with
			ts (uint): The timestamp to store
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = 'UPDATE `%(db)s`.`%(table)s`\n' \
			'SET `timestamp` = FROM_UNIXTIME(%(ts)d)\n' \
			'WHERE `user` = %(user)d' % {
				"db": dStruct['db'],
				"table": dStruct['table'],
				"ts": ts,
				"user": user
			}

		# Attempt to update the timestamp
		iRows = Record_MySQL.Commands.execute(
			dStruct['host'],
			sSQL
		)

		# If we updated nothing
		if not iRows:

			# Create the new record
			try:
				oRecord = cls({
					"user": user,
					"timestamp": ts
				})
				oRecord.create()
			except Record_MySQL.DuplicateException:
				pass

# CustomerCommunication class
class CustomerCommunication(Record_MySQL.Record):
	"""CustomerCommunication

	Represents a message to or from a customer or potential customer
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
				Tree.fromFile('definitions/monolith/customer_communication.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def newMessages(cls, numbers, ts, custom={}):
		"""New Messages

		Checks for new messages from the given numbers

		Arguments:
			numbers (str[]): List of phone numbers to check
			ts (uint): Timestamp indicating last check
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Init the return
		dRet = {}

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the list of numbers
		lNumbers = []
		for s in numbers:
			s = Record_MySQL.Commands.escape(dStruct['host'], s)
			lNumbers.extend([s, '1%s' % s])

		# Generate SQL
		sSQL = "SELECT\n" \
				"	`fromPhone`, count(`fromPhone`) as `count`\n" \
				"FROM\n" \
				"	`%(db)s`.`%(table)s`\n" \
				"WHERE\n" \
				"	`createdAt` > FROM_UNIXTIME(%(ts)d) AND\n" \
				"	`fromPhone` IN (%(numbers)s)\n" \
				"GROUP BY\n" \
				"	`fromPhone`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"ts": ts,
			"numbers": "'%s'" % "','".join(lNumbers)
		}

		# Fetch the data
		lRecords = Record_MySQL.Commands.select(dStruct['host'], sSQL)

		# Return
		return {d['fromPhone']:d['count'] for d in lRecords}

	@classmethod
	def thread(cls, number, custom={}):
		"""Thread

		Fetches all the records in or out associated with a phone number in
		chronological order

		Arguments:
			number (str): The phone number to look up
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sConversationSQL % {
				"db": dStruct['db'],
				"table": dStruct['table'],
				"number": Record_MySQL.Commands.escape(dStruct['host'], number)
			}
		)

# CustomerMsgPhone class
class CustomerMsgPhone(Record_MySQL.Record):
	"""CustomerMsgPhone

	Represents a summary of all messages to and from a customer or potential
	customer
	"""

	_conf = None
	"""Configuration"""

	INCOMING = 0
	OUTGOING = 1
	"""Direction"""

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
				Tree.fromFile('definitions/monolith/customer_msg_phone.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def add(cls, direction, customerPhone, date, message, custom={}):
		"""Add

		Adds an incoming or outgoing message to the conversation summary

		Arguments:
			direction (uint): The direction INCOMING/OUTGOING of the message
			customerPhone (str): The number associated with the conversation
			message (str): The message to prepend to the conversation
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# If the message is incoming
		if direction is cls.INCOMING:
			sDirection = 'Incoming'
			sHidden = 'N'
			sIncrement = 'totalIncoming'
		elif direction is cls.OUTGOING:
			sDirection = 'Outgoing'
			sHidden = 'Y'
			sIncrement = 'totalOutGoing'
		else:
			raise ValueError('Direction must be one of INCOMING or OUTGOING')

		# Generate SQL
		sSQL = "UPDATE `%(db)s`.`%(table)s` SET\n" \
				"	`lastMsgDir` = '%(direction)s',\n" \
				"	`lastMsgAt` = '%(date)s',\n" \
				"	`hiddenFlag` = '%(hidden)s',\n" \
				"	`%(increment)s` = `%(increment)s` + 1,\n" \
				"	`lastMsg` = CONCAT('%(message)s', IFNULL(`lastMsg`, ''))\n" \
				"WHERE `customerPhone` = '%(customerPhone)s'" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"date": date,
			"direction": sDirection,
			"message": Record_MySQL.Commands.escape(dStruct['host'], message),
			"customerPhone": Record_MySQL.Commands.escape(dStruct['host'], customerPhone),
			"hidden": sHidden,
			"increment": sIncrement
		}

		# Execute the update
		return Record_MySQL.Commands.execute(dStruct['host'], sSQL)

	@classmethod
	def claimed(cls, user, custom={}):
		"""Claimed

		Returns all the conversations the user has claimed

		Arguments:
			user (int): The ID of the user
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT\n" \
				"	`cmp`.`customerPhone`,\n" \
				"	`cmp`.`customerName`,\n" \
				"	`cc`.`transferredBy`,\n" \
				"	`cc`.`provider`\n," \
				"	`cc`.`orderId`\n" \
				"FROM\n" \
				"	`%(db)s`.`%(table)s` AS `cmp` JOIN\n" \
				"	`%(db)s`.`customer_claimed` as `cc` ON\n" \
				"		`cmp`.`customerPhone` = `cc`.`phoneNumber`\n" \
				"WHERE\n" \
				"	`cc`.`user` = %(user)d\n" \
				"ORDER BY\n" \
				"	`cc`.`provider` DESC, `cc`.`transferredBy` DESC, `cc`.`createdAt`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"user": user
		}

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	@classmethod
	def search(cls, q, custom={}):
		"""Search

		Search conversations and return them

		Arguments:
			q (dict): The strings to query
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL Where
		lWhere = []
		if 'phone' in q and q['phone']:
			lWhere.append("`customerPhone` LIKE '%%%s%%'" % Record_MySQL.Commands.escape(dStruct['host'], q['phone'][-10:]))
		if 'name' in q and q['name']:
			lWhere.append("`customerName` LIKE '%%%s%%'" % Record_MySQL.Commands.escape(dStruct['host'], q['name']))
		if 'content' in q and q['content']:
			lWhere.append("`lastMsg` LIKE '%%%s%%'" % Record_MySQL.Commands.escape(dStruct['host'], q['content']))

		# Generate SQL
		sSQL = sSearchSQL % {
			"db": dStruct['db'],
			"where": ' AND '.join(lWhere)
		}

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	@classmethod
	def unclaimed(cls, order='ASC', custom={}):
		"""Unclaimed

		Fetches open conversations that have not been claimed by any agent

		Arguments:
			order (str): Order by ASC or DESC
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
				"	`cmp`.`id` AS `id`,\n" \
				"	`cmp`.`customerPhone` AS `customerPhone`,\n" \
				"	IFNULL(`cmp`.`customerName`, 'N/A') AS `customerName`,\n" \
				"	CONVERT(`ktot`.`customerId`, UNSIGNED) as `customerId`,\n" \
				"	`ktot`.`numberOfOrders` AS `numberOfOrders`,\n" \
				"	`ktot`.`latest_kto_id` AS `latest_kto_id`,\n" \
				"	`cmp`.`lastMsgAt` as `lastMsgAt`,\n" \
				"	`cmp`.`lastMsg` AS `lastMsg`,\n" \
				"	`cmp`.`totalIncoming` AS `totalIncoming`,\n" \
				"	`cmp`.`totalOutGoing` AS `totalOutGoing`\n" \
				"FROM `%(db)s`.`customer_msg_phone` AS `cmp`\n" \
				"LEFT JOIN (\n" \
				"	SELECT `cmp1`.`id` AS `id`, COUNT(0) AS `numberOfOrders`,\n" \
				"			MAX(`kto`.`id`) AS `latest_kto_id`, `kto`.`customerId`\n" \
				"	FROM `%(db)s`.`customer_msg_phone` `cmp1`\n" \
				"	JOIN `%(db)s`.`kt_order` AS `kto` ON (\n" \
				"		`cmp1`.`customerPhone` = SUBSTR(`kto`.`phoneNumber`, -(10))\n" \
				"		AND ((`kto`.`cardType` <> 'TESTCARD')\n" \
				"		OR ISNULL(`kto`.`cardType`))\n" \
				"	)\n" \
				"	GROUP BY `cmp1`.`id`\n" \
				") `ktot` ON `ktot`.`id` = `cmp`.`id`\n" \
				"LEFT JOIN `%(db)s`.`customer_claimed` as `cc` ON `cc`.`phoneNumber` = `cmp`.`customerPhone`\n" \
				"WHERE `hiddenFlag` = 'N'\n" \
				"AND `lastMsgDir` = 'Incoming'\n" \
				"AND `cc`.`user` IS NULL\n" \
				"ORDER BY `cmp`.`lastMsgAt` %(order)s" % {
			"db": dStruct['db'],
			"order": order
		}

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	@classmethod
	def unclaimedCount(cls, custom={}):
		"""Unclaimed Count

		Fetches the count of open conversations that have not been claimed by
		any agent

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT\n" \
				"	COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`customer_msg_phone` AS `cmp`\n" \
				"LEFT JOIN (\n" \
				"	SELECT `cmp1`.`id` AS `id`, COUNT(0) AS `numberOfOrders`,\n" \
				"			MAX(`kto`.`id`) AS `latest_kto_id`, `kto`.`customerId`\n" \
				"	FROM `%(db)s`.`customer_msg_phone` `cmp1`\n" \
				"	JOIN `%(db)s`.`kt_order` AS `kto` ON (\n" \
				"		`cmp1`.`customerPhone` = SUBSTR(`kto`.`phoneNumber`, -(10))\n" \
				"		AND ((`kto`.`cardType` <> 'TESTCARD')\n" \
				"		OR ISNULL(`kto`.`cardType`))\n" \
				"	)\n" \
				"	GROUP BY `cmp1`.`id`\n" \
				") `ktot` ON `ktot`.`id` = `cmp`.`id`\n" \
				"LEFT JOIN `%(db)s`.`customer_claimed` as `cc` ON `cc`.`phoneNumber` = `cmp`.`customerPhone`\n" \
				"WHERE `hiddenFlag` = 'N'\n" \
				"AND `lastMsgDir` = 'Incoming'\n" \
				"AND `cc`.`user` IS NULL\n" % {
			"db": dStruct['db']
		}

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.CELL
		)

# DsPatient class
class DsPatient(Record_MySQL.Record):
	"""DsPatient

	Represents a customer in DoseSpot
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
				Tree.fromFile('definitions/monolith/ds_patient.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Forgot class
class Forgot(Record_MySQL.Record):
	"""Forgot

	Represents an attempt to reset a forgotten password
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
				Tree.fromFile('definitions/monolith/forgot.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# HrtLabResultTests class
class HrtLabResultTests(Record_MySQL.Record):
	""""HRT Lab Result Tests

	Represents a customers lab results test values in memo
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
				Tree.fromFile('definitions/monolith/hrt_lab_result_tests.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# KtCustomer class
class KtCustomer(Record_MySQL.Record):
	"""KtCustomer

	Represents a customer in konnektive
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def byNameAndZip(cls, name, zip_, custom={}):
		"""By Phone

		Returns the ID and claimed state of the customer from their phone number

		Arguments:
			name (str): The full shipping name of the customer
			zip (str): The shipping zip code of the customer
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT `customerId`, `emailAddress`, `phoneNumber`, `firstName`, `lastName` " \
				"FROM `%(db)s`.`%(table)s` " \
				"WHERE CONCAT(`shipFirstName`, ' ', `shipLastName`) = '%(name)s' " \
				"AND `shipPostalCode` = '%(zip)s' " \
				"ORDER BY `updatedAt` DESC " \
				"LIMIT 1" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"name": Record_MySQL.Commands.escape(dStruct['host'], name),
			"zip": Record_MySQL.Commands.escape(dStruct['host'], zip_)
		}

		# Execute and return the select
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ROW
		)

	@classmethod
	def byPhone(cls, number, custom={}):
		"""By Phone

		Returns the ID and claimed state of the customer from their phone number

		Arguments:
			number (str): The phone number of the customer
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT " \
				"CONVERT(`ktc`.`customerId`, UNSIGNED) as `customerId`, " \
				"CONCAT(`ktc`.`firstName`, ' ', `ktc`.`lastName`) as `customerName`, " \
				"`cc`.`user` as `claimedUser` " \
				"FROM `%(db)s`.`%(table)s` as `ktc` " \
				"LEFT JOIN `%(db)s`.`customer_claimed` as `cc` ON `ktc`.`phoneNumber` = `cc`.`phoneNumber` " \
				"WHERE `ktc`.`phoneNumber` IN ('%(number)s', '1%(number)s') " \
				"ORDER BY `ktc`.`updatedAt` DESC " \
				"LIMIT 1" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"number": Record_MySQL.Commands.escape(dStruct['host'], number)
		}

		# Execute and return the select
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ROW
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
				Tree.fromFile('definitions/monolith/kt_customer.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# KtOrder class
class KtOrder(Record_MySQL.Record):
	"""KtOrder

	Represents a customer's order in konnektive
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def claimed(cls, user, custom={}):
		"""Claimed

		Returns all the customers the user has claimed

		Arguments:
			user (int): The ID of the user
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
				"	`ktoc`.`customerId`,\n" \
				"	`ktoc`.`orderId`,\n" \
				"	`ktoc`.`transferredBy`,\n" \
				"	`ktoc`.`continuous`,\n" \
				"	CONCAT(`ktc`.`firstName`, ' ', `ktc`.`lastName`) as `customerName`,\n" \
				"	`c`.`type`\n" \
				"FROM\n" \
				"	`%(db)s`.`%(table)s` as `kto`,\n" \
				"	`%(db)s`.`kt_customer` as `ktc`,\n" \
				"	`%(db)s`.`kt_order_claim` as `ktoc`,\n" \
				"	`%(db)s`.`campaign` as `c`\n" \
				"WHERE\n" \
				"	`ktoc`.`user` = %(user)d AND\n" \
				"	CONVERT(`ktc`.`customerId`, UNSIGNED) = `ktoc`.`customerId` AND\n" \
				"	`kto`.`orderId` = `ktoc`.`orderId` AND\n" \
				"	`kto`.`campaignId` = `c`.`id`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"user": user
		}

		# Fetch and return the data
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
				Tree.fromFile('definitions/monolith/kt_order.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def claimDetails(cls, order_id, custom={}):
		"""Claim Details

		Gets the campaign and customer name associated with the order, details
		useful for claims

		Arguments:
			order_id (str): The ID of the order
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
				"	`kto`.`customerId`,\n" \
				"	CONCAT(`ktc`.`firstName`, ' ', `ktc`.`lastName`) as `customerName`,\n" \
				"	`c`.`type`\n" \
				"FROM\n" \
				"	`%(db)s`.`%(table)s` as `kto`,\n" \
				"	`%(db)s`.`kt_customer` as `ktc`,\n" \
				"	`%(db)s`.`campaign` as `c`\n" \
				"WHERE\n" \
				"	`kto`.`orderId` = '%(order)s' AND\n" \
				"	`kto`.`customerId` = `ktc`.`customerId` AND\n" \
				"	`kto`.`campaignId` = `c`.`id`" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"order": Record_MySQL.Commands.escape(dStruct['host'], order_id)
		}

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ROW
		)

	@classmethod
	def distinctCampaigns(cls, custom={}):
		"""Distinct Campaigns

		Returns the set of campaign IDs associated with orders

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = "SELECT DISTINCT CONVERT(`campaignId`, UNSIGNED) as `id`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"ORDER BY `id`" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Return the IDs as a list
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.COLUMN
		)

	@classmethod
	def ordersByPhone(cls, phone, custom={}):
		"""Orders By Phone

		Returns the count of orders by a specific phone number

		Arguments:
			phone (str): The phone number associated with the
				conversation
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Fetch the orders
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sNumOfOrdersSQL % {
				"db": dStruct['db'],
				"table": dStruct['table'],
				"phone": Record_MySQL.Commands.escape(dStruct['host'], phone)
			},
			Record_MySQL.ESelect.COLUMN
		)

	@classmethod
	def queueCsr(cls, custom={}):
		"""Queue CSR

		Returns all pending, unclaimed, orders with a role of CSR

		Arguments:
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
				"	`kto`.`orderId`,\n" \
				"	CONCAT(`kto`.`shipFirstName`, ' ', `kto`.`shipLastName`) as `customerName`,\n" \
				"	`kto`.`phoneNumber` as `customerPhone`,\n" \
				"	`kto`.`shipCity`,\n" \
				"	IFNULL(`ss`.`name`, '[state missing]') as `shipState`,\n" \
				"	IFNULL(`ss`.`legalEncounterType`, '') as `type`,\n" \
				"	CONVERT(`kto`.`customerId`, UNSIGNED) as `customerId`,\n" \
				"	`kto`.`dateCreated`,\n" \
				"	`kto`.`dateUpdated`,\n" \
				"	IFNULL(`os`.`attentionRole`, 'Not Assigned') AS `attentionRole`,\n" \
				"	IFNULL(`os`.`orderLabel`, 'Not Labeled') AS `orderLabel`\n" \
				"FROM `%(db)s`.`%(table)s` AS `kto`\n" \
				"LEFT JOIN `%(db)s`.`smp_state` as `ss` ON `ss`.`abbreviation` = `kto`.`shipState`\n" \
				"LEFT JOIN `%(db)s`.`smp_order_status` as `os` ON `os`.`orderId` = `kto`.`orderId`\n" \
				"LEFT JOIN `%(db)s`.`customer_claimed` as `cc` ON `cc`.`phoneNumber` = `kto`.`phoneNumber`\n" \
				"WHERE `kto`.`orderStatus` = 'PENDING'\n" \
				"AND IFNULL(`kto`.`cardType`, '') <> 'TESTCARD'\n" \
				"AND `cc`.`user` IS NULL\n" \
				"AND `attentionRole` = 'CSR'\n" \
				"ORDER BY `kto`.`dateCreated` ASC" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	@classmethod
	def queueCsrCount(cls, custom={}):
		"""Queue CSR Count

		Returns just the count of pending, unclaimed, orders with a role of CSR

		Arguments:
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
				"	COUNT(*) as `count`\n" \
				"FROM `%(db)s`.`%(table)s` AS `kto`\n" \
				"LEFT JOIN `%(db)s`.`smp_order_status` as `os` ON `os`.`orderId` = `kto`.`orderId`\n" \
				"LEFT JOIN `%(db)s`.`customer_claimed` as `cc` ON `cc`.`phoneNumber` = `kto`.`phoneNumber`\n" \
				"WHERE `kto`.`orderStatus` = 'PENDING'\n" \
				"AND IFNULL(`kto`.`cardType`, '') <> 'TESTCARD'\n" \
				"AND `cc`.`user` IS NULL\n" \
				"AND `attentionRole` = 'CSR'\n" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.CELL
		)

	@classmethod
	def queue(cls, group, states, custom={}):
		"""Queue

		Returns all pending, unclaimed, orders in the given states

		Arguments:
			group (str): 'ed' or 'hrt'
			states (list): The states to check for pending orders in
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
				"	`kto`.`orderId`,\n" \
				"	CONCAT(`kto`.`shipFirstName`, ' ', `kto`.`shipLastName`) as `customerName`,\n" \
				"	`kto`.`phoneNumber` as `customerPhone`,\n" \
				"	`kto`.`shipCity`,\n" \
				"	IFNULL(`ss`.`name`, '[state missing]') as `shipState`,\n" \
				"	IFNULL(`ss`.`legalEncounterType`, '') as `encounter`,\n" \
				"	CONVERT(`kto`.`customerId`, UNSIGNED) as `customerId`,\n" \
				"	`kto`.`dateCreated`,\n" \
				"	`kto`.`dateUpdated`,\n" \
				"	IFNULL(`os`.`attentionRole`, 'Not Assigned') as `attentionRole`,\n" \
				"	IFNULL(`os`.`orderLabel`, 'Not Labeled') as `orderLabel`\n" \
				"FROM `%(db)s`.`%(table)s` as `kto`\n" \
				"JOIN `%(db)s`.`campaign` as `cmp` ON `cmp`.`id` = CONVERT(`kto`.`campaignId`, UNSIGNED)\n" \
				"LEFT JOIN `%(db)s`.`smp_state` as `ss` ON `ss`.`abbreviation` = `kto`.`shipState`\n" \
				"LEFT JOIN `%(db)s`.`smp_order_status` as `os` ON `os`.`orderId` = `kto`.`orderId`\n" \
				"LEFT JOIN `%(db)s`.`kt_order_claim` as `ktoc` ON `ktoc`.`customerId` = CONVERT(`kto`.`customerId`, UNSIGNED)\n" \
				"WHERE `kto`.`orderStatus` = 'PENDING'\n" \
				"AND IFNULL(`kto`.`cardType`, '') <> 'TESTCARD'\n" \
				"AND `kto`.`shipState` IN (%(states)s)\n" \
				"AND `ktoc`.`user` IS NULL\n" \
				"AND `cmp`.`type` = '%(group)s'\n" \
				"AND (`os`.`attentionRole` = 'Doctor' OR `os`.`attentionRole` IS NULL)\n" \
				"ORDER BY `kto`.`dateUpdated` ASC" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"group": group,
			"states": "'%s'" % "','".join(states)
		}

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# KtOrderClaim class
class KtOrderClaim(Record_MySQL.Record):
	"""KtOrderClaim

	Represents a claim of a customer/order by a user
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
				Tree.fromFile('definitions/monolith/kt_order_claim.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# KtOrderClaimLast class
class KtOrderClaimLast(Record_MySQL.Record):
	"""KtOrderClaimLast

	Represents the last time a user looked up new notes on claimed
	customers
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
				Tree.fromFile('definitions/monolith/kt_order_claim_last.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def get(cls, user, custom={}):
		"""Get

		Get's the last timestamp for the given user

		Arguments:
			user (uint): The user to get the timestamp for
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			uint
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = 'SELECT UNIX_TIMESTAMP(`timestamp`)\n' \
			'FROM `%(db)s`.`%(table)s`\n' \
			'WHERE `user` = %(user)d' % {
				"db": dStruct['db'],
				"table": dStruct['table'],
				"user": user
			}

		# Fetch the value
		iTS = Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.CELL
		)

		# If we got no value
		if not iTS:
			iTS = int(time())

		# Return the timestamp
		return iTS

	@classmethod
	def set(cls, user, ts, custom={}):
		"""Set

		Updates the current value for the user or else creates it

		Arguments:
			user (uint): The unique ID of the user the timestamp is
				associated with
			ts (uint): The timestamp to store
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL
		sSQL = 'UPDATE `%(db)s`.`%(table)s`\n' \
			'SET `timestamp` = FROM_UNIXTIME(%(ts)d)\n' \
			'WHERE `user` = %(user)d' % {
				"db": dStruct['db'],
				"table": dStruct['table'],
				"ts": ts,
				"user": user
			}

		# Attempt to update the timestamp
		iRows = Record_MySQL.Commands.execute(
			dStruct['host'],
			sSQL
		)

		# If we updated nothing
		if not iRows:

			# Create the new record
			try:
				oRecord = cls({
					"user": user,
					"timestamp": ts
				})
				oRecord.create()
			except Record_MySQL.DuplicateException:
				pass

# KtOrderContinuous class
class KtOrderContinuous(Record_MySQL.Record):
	"""KtOrderContinuous

	Represents an order that needs to be extended with a new MIP/Prescription(s)
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
				Tree.fromFile('definitions/monolith/kt_order_continuous.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def queue(cls, group, states, custom={}):
		"""Queue

		Returns all pending, unclaimed, continuous orders in the given states

		Arguments:
			group (str): 'ed' or 'hrt'
			states (list): The states to check for pending orders in
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
				"	`cont`.`status`,\n" \
				"	`kto`.`orderId`,\n" \
				"	CONCAT(`kto`.`shipFirstName`, ' ', `kto`.`shipLastName`) as `customerName`,\n" \
				"	`kto`.`phoneNumber` as `customerPhone`,\n" \
				"	`kto`.`shipCity`,\n" \
				"	IFNULL(`ss`.`name`, '[state missing]') as `shipState`,\n" \
				"	IFNULL(`ss`.`legalEncounterType`, '') as `encounter`,\n" \
				"	CONVERT(`kto`.`customerId`, UNSIGNED) as `customerId`,\n" \
				"	`kto`.`dateCreated`,\n" \
				"	`kto`.`dateUpdated`,\n" \
				"	IFNULL(`os`.`attentionRole`, 'Not Assigned') as `attentionRole`,\n" \
				"	IFNULL(`os`.`orderLabel`, 'Not Labeled') as `orderLabel`\n" \
				"FROM `%(db)s`.`%(table)s` as `cont`\n" \
				"JOIN `%(db)s`.`kt_order` as `kto` ON `kto`.`orderId` = `cont`.`orderId`\n" \
				"JOIN `%(db)s`.`campaign` as `cmp` ON `cmp`.`id` = CONVERT(`kto`.`campaignId`, UNSIGNED)\n" \
				"LEFT JOIN `%(db)s`.`smp_state` as `ss` ON `ss`.`abbreviation` = `kto`.`shipState`\n" \
				"LEFT JOIN `%(db)s`.`smp_order_status` as `os` ON `os`.`orderId` = `kto`.`orderId`\n" \
				"LEFT JOIN `%(db)s`.`kt_order_claim` as `ktoc` ON `ktoc`.`customerId` = CONVERT(`kto`.`customerId`, UNSIGNED)\n" \
				"WHERE `cont`.`status` = 'PENDING'\n" \
				"AND `cont`.`active` = 1\n" \
				"AND `kto`.`shipState` IN (%(states)s)\n" \
				"AND `ktoc`.`user` IS NULL\n" \
				"AND `cmp`.`type` = '%(group)s'\n" \
				"AND (`os`.`attentionRole` = 'Doctor' OR `os`.`attentionRole` IS NULL)\n" \
				"ORDER BY `kto`.`dateUpdated` ASC" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"group": group,
			"states": "'%s'" % "','".join(states)
		}

		print(sSQL)

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# ShippingInfo class
class ShippingInfo(Record_MySQL.Record):
	"""ShippingInfo

	Represents a tracking code associated with a customer
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
				Tree.fromFile('definitions/monolith/shipping_info.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# SmpNote class
class SmpNote(Record_MySQL.Record):
	"""SmpNote

	Represents an internal note associated with a customer
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def byCustomer(cls, customer_id, custom={}):
		"""By Customer

		Fetches all notes associated with the customer's orders

		Arguments:
			customer_id (int): The unique ID of the customer
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = sSmpNotes % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"id": customer_id
		}

		# Execute and return the select
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
				Tree.fromFile('definitions/monolith/smp_note.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def newNotes(cls, ids, ts, custom={}):
		"""New Notes

		Returns if there's any new notes associated with the given customer
		IDs

		Arguments:
			ids (int[]): A list of unique customer IDs
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			list
		"""

		# Init the return
		dRet = {}

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = sSmpNotesNew % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"ts": ts,
			"ids": "'%s'" % "','".join([str(d) for d in ids])
		}

		# Fetch the data
		lRecords = Record_MySQL.Commands.select(dStruct['host'], sSQL)

		# Return
		return {d['customerId']:d['count'] for d in lRecords}

# SmpOrderStatus class
class SmpOrderStatus(Record_MySQL.Record):
	"""SmpOrderStatus

	Represents status info on a specific order
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
				Tree.fromFile('definitions/monolith/smp_order_status.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def latest(cls, customer_id, custom={}):
		"""Latest

		Fetches the order status for the most recent order by customer

		Arguments:
			customer_id (int): The ID of the customer
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = sLatestStatusSQL % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"customerId": customer_id
		}

		# Execute and return the select
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ROW
		)

# SmpState class
class SmpState(Record_MySQL.Record):
	"""SmpState

	Represents states and their encounter types
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
				Tree.fromFile('definitions/monolith/smp_state.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# SMSPatientWorkflow class
class SMSPatientWorkflow(Record_MySQL.Record):
	"""SMS Patient Workflow

	Represents the current state of a new customer in the sms workflow
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
				Tree.fromFile('definitions/monolith/sms_patient_workflow.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# SMSStop class
class SMSStop(Record_MySQL.Record):
	"""SMSStop

	Represents a customer phone number that should be blocked
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
				Tree.fromFile('definitions/monolith/sms_stop.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# SMSTemplate class
class SMSTemplate(Record_MySQL.Record):
	"""SMSTemplate

	Represents an SMS template for the workflow
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
				Tree.fromFile('definitions/monolith/sms_template.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# TfAnswer class
class TfAnswer(Record_MySQL.Record):
	"""TfAnswer

	Represents a customer phone number that should be blocked
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def allergies(cls, landing_id, custom={}):
		"""Allergies

		Finds and returns the allergies answer

		Arguments:
			landing_id (str): The unique landing ID
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Look for answers for the specific questions
		dAnswer = TfAnswer.filter({
			"landing_id": landing_id,
			"ref": ['95f9516a-4670-43b1-9b33-4cf822dc5917', 'allergies']
		}, raw=['value'], limit=1);

		# If there's no answer
		if not dAnswer:
			return False;

		# Return the answer
		return dAnswer['value']

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
				Tree.fromFile('definitions/monolith/tf_answer.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def dob(cls, landing_id, custom={}):
		"""DOB

		Finds and returns the date of birth answer

		Arguments:
			landing_id (str): The unique landing ID
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Look for answers for the specific questions
		dAnswer = TfAnswer.filter({
			"landing_id": landing_id,
			"ref": ['b63763bc7f3b71dc', 'birthdate']
		}, raw=['value'], limit=1);

		# If there's no answer
		if not dAnswer:
			return False;

		# Return the answer
		return dAnswer['value']

# TfLanding class
class TfLanding(Record_MySQL.Record):
	"""TfLanding

	Represents a customer phone number that should be blocked
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
				Tree.fromFile('definitions/monolith/tf_landing.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def find(cls, last_name, email, phone, form=None, custom={}):
		"""Find

		Attempts to find landings using customer info

		Arguments:
			last_name (str): The last name of the customer
			email (str): The email of the customer
			phone (str): The phone number of the customer
			form (str[str[]): A form type of types to filter by
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Where clauses
		lWhere = [
			"`lastName` = '%s'" % Record_MySQL.Commands.escape(dStruct['host'], last_name),
			"`birthDay` IS NOT NULL",
			"`birthDay` != ''",
			"(`email` = '%(email)s' OR `phone` IN ('1%(phone)s', '%(phone)s'))" % {
				"email": Record_MySQL.Commands.escape(dStruct['host'], email),
				"phone": Record_MySQL.Commands.escape(dStruct['host'], phone)
			}
		]

		# If we have a form type or types
		if form:
			if isinstance(form, str):
				lWhere.append(
					"`formId` = '%s'" % Record_MySQL.Commands.escape(dStruct['host'], form)
				)
			elif isinstance(form, list):
				form = [Record_MySQL.Commands.escape(dStruct['host'], s) for s in form]
				lWhere.append(
					"`formId` IN ('%s')" % "','".join(form)
				)
			else:
				raise ValueError('form must be str|str[]')

		# Generate SQL
		sSQL = "SELECT `landing_id`, `formId`, `submitted_at`, `complete`\n" \
				"FROM `%(db)s`.`%(table)s`\n" \
				"WHERE %(where)s\n" \
				"ORDER BY `submitted_at` DESC\n" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"where": '\nAND'.join(lWhere)
		}

		# Execute and return the select
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# TfQuestion class
class TfQuestion(Record_MySQL.Record):
	"""TfQuestion

	Represents a customer phone number that should be blocked
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
				Tree.fromFile('definitions/monolith/tf_question.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# TfQuestionOption class
class TfQuestionOption(Record_MySQL.Record):
	"""TfQuestionOption

	Represents a customer phone number that should be blocked
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
			cls._conf =  Record_MySQL.Record.generateConfig(
				Tree.fromFile('definitions/monolith/tf_question_option.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# User class
class User(Record_MySQL.Record):
	"""User

	Represents a Memo user
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
				Tree.fromFile('definitions/monolith/user.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def passwordStrength(cls, passwd):
		"""Password Strength

		Returns true if a password is secure enough

		Arguments:
			passwd (str): The password to check

		Returns:
			bool
		"""

		# If we don't have enough or the right chars
		if 8 > len(passwd) or \
			100 < len(passwd) or \
			re.search(r'[A-Z]+', passwd) == None or \
			re.search(r'[a-z]+', passwd) == None or \
			re.search(r'[0-9]+', passwd) == None or \
			re.search(r'\s+', passwd) or \
			passwd in ['Passw0rd', 'Password123']:

			# Invalid password
			return False

		# Return OK
		return True
