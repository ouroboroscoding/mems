# coding=utf8
""" WellDyne Records

Handles the record structures for the monolith service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-07-03"

# Python imports
import copy
from hashlib import sha1
import re

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# AdHoc class
class AdHoc(Record_MySQL.Record):
	"""AdHoc

	Represents an adhoc entry that needs to be sent to WellDyne
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
				Tree.fromFile('definitions/welldyne/adhoc.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def display(cls, custom={}):
		"""Display

		Returns all adhoc records with the data in triggers suitable for
		displaying

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT\n" \
				"	`wda`.`_id` as `_id`,\n" \
				"	`wda`.`type` as `type`,\n" \
				"	`wda`.`memo_user` as `memo_user`,\n" \
				"	`wdt`.`crm_type` as `crm_type`,\n" \
				"	`wdt`.`crm_id` as `crm_id`,\n" \
				"	`wdt`.`crm_order` as `crm_order`\n" \
				"FROM `%(db)s`.`%(table)s` as `wda`\n" \
				"JOIN `%(db)s`.`welldyne_trigger` as `wdt` ON `wda`.`trigger_id` = `wdt`.`_id`\n" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Execute the SQL
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	@classmethod
	def report(cls, custom={}):
		"""Report

		Returns the raw data from the triggers associated to the records in the
		table

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT\n" \
				"	`wda`.`_id` as `_id`,\n" \
				"	`wda`.`trigger_id` as `trigger_id`,\n" \
				"	`wda`.`type` as `type`,\n" \
				"	`wdt`.`crm_id` as `crm_id`,\n" \
				"	`wdt`.`raw` as `raw`\n" \
				"FROM `%(db)s`.`%(table)s` as `wda`\n" \
				"JOIN `%(db)s`.`welldyne_trigger` as `wdt` ON `wda`.`trigger_id` = `wdt`.`_id`\n" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Execute the SQL
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# AdHocManual class
class AdHocManual(Record_MySQL.Record):
	"""AdHocManual

	Represents an adhoc entry that needs to be sent to WellDyne
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
				Tree.fromFile('definitions/welldyne/adhoc_manual.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def display(cls, custom={}):
		"""Display

		Returns all adhoc records with the data in triggers suitable for
		displaying

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT\n" \
				"	`wda`.`_id` as `_id`,\n" \
				"	`wdt`.`crm_type` as `crm_type`,\n" \
				"	`wdt`.`crm_id` as `crm_id`,\n" \
				"	`wdt`.`crm_order` as `crm_order`\n" \
				"FROM `%(db)s`.`%(table)s` as `wda`\n" \
				"JOIN `%(db)s`.`welldyne_trigger` as `wdt` ON `wda`.`trigger_id` = `wdt`.`_id`\n" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Execute the SQL
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

	def move(self):
		"""Move

		Moves the record from Manual to the actual table

		Returns:
			None
		"""

		# If the record lacks a primary key (never been created/inserted)
		if self._dStruct['primary'] not in self._dRecord:
			raise KeyError(self._dStruct['primary'])

		# Generate the necessary fields
		sFields = '`trigger_id`, `type`, `memo_user`'

		# Statemens
		lStatements = [
			"INSERT INTO `%(db)s`.`%(table)s` (`%(primary)s`, %(fields)s)\n" \
				"SELECT UUID(), %(fields)s FROM `%(db)s`.`%(table_manual)s`\n" \
				"WHERE `%(primary)s` = '%(_id)s'\n",
			"DELETE FROM `%(db)s`.`%(table_manual)s`\n" \
				"WHERE `%(primary)s` = '%(_id)s'"
		]

		# Go through each statement
		for s in lStatements:

			# Generate the SQL using the variables
			sSQL = s % {
				"db": self._dStruct['db'],
				"table": self._dStruct['table'][:-7],
				"table_manual": self._dStruct['table'],
				"fields": sFields,
				"primary": self._dStruct['primary'],
				"_id": self._dRecord[self._dStruct['primary']]
			}

			# Execute the SQL
			Record_MySQL.Commands.execute(
				self._dStruct['host'],
				sSQL
			)

# Eligibility class
class Eligibility(Record_MySQL.Record):
	"""Eligibility

	Represents an customers eligibility with Welldyne
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
				Tree.fromFile('definitions/monolith/wd_eligibility.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def withCustomerData(cls, custom={}):
		"""With Customer Data

		Fetches data for generating the actually eligibility report

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict[]
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the SQL to fetch all valid records with the customer data
		#	and DOB
		sSQL = "SELECT\n" \
				"	`wde`.`customerId` AS `customerId`,\n" \
				"	`wde`.`memberSince` AS `memberSince`,\n" \
				"	`wde`.`memberThru` AS `memberThru`,\n" \
				"	`ktc`.`shipFirstName` AS `shipFirstName`,\n" \
				"	`ktc`.`shipLastName` AS `shipLastName`,\n" \
				"	`ktc`.`shipAddress1` AS `shipAddress1`,\n" \
				"	`ktc`.`shipAddress2` AS `shipAddress2`,\n" \
				"	`ktc`.`shipCity` AS `shipCity`,\n" \
				"	`ktc`.`shipState` AS `shipState`,\n" \
				"	`ktc`.`shipPostalCode` AS `shipPostalCode`,\n" \
				"	`ktc`.`shipCountry` AS `shipCountry`,\n" \
				"	`ktc`.`phoneNumber` AS `phoneNumber`,\n" \
				"	`ktc`.`emailAddress` AS `emailAddress`,\n" \
				"	CAST(`dsp`.`dateOfBirth` AS DATE) AS `dob`\n" \
				"FROM\n" \
				"	((`%(db)s`.`%(table)s` as `wde`\n" \
				"	JOIN `%(db)s`.`kt_customer` as `ktc` USING (`customerId`))\n" \
				"	JOIN `%(db)s`.`ds_patient` as `dsp` USING (`customerId`))\n" \
				"WHERE `wde`.`memberThru` != '0000-00-00 00:00:00'" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Run the select and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# Outbound class
class Outbound(Record_MySQL.Record):
	"""Outbound

	Represents an outbound failure entry sent by Welldyne
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def deleteNotReady(cls, custom={}):
		"""Delete Not Ready

		Deletes all records in the table that aren't marked as ready

		Arguments:
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = 'DELETE FROM `%(db)s`.`%(table)s`\n' \
				'WHERE `ready` = 0' % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Execute and return the select
		return Record_MySQL.Commands.execute(
			dStruct['host'],
			sSQL
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
				Tree.fromFile('definitions/welldyne/outbound.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	def sent(self):
		"""Sent

		Moves the record to the sent table

		Returns:
			None
		"""

		# If the record lacks a primary key (never been created/inserted)
		if self._dStruct['primary'] not in self._dRecord:
			raise KeyError(self._dStruct['primary'])

		# Generate the necessary fields
		sFields = '`crm_type`, `crm_id`, `crm_order`'

		# Statemens
		lStatements = [
			"INSERT INTO `%(db)s`.`%(table)s_sent` (`%(primary)s`, %(fields)s)\n" \
				"SELECT UUID(), %(fields)s FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `%(primary)s` = '%(_id)s'\n" \
				"ON DUPLICATE KEY UPDATE `attempts` = `attempts` + 1",
			"DELETE FROM `%(db)s`.`%(table)s`\n" \
				"WHERE `%(primary)s` = '%(_id)s'"
		]

		# Go through each statement
		for s in lStatements:

			# Generate the SQL using the variables
			sSQL = s % {
				"db": self._dStruct['db'],
				"table": self._dStruct['table'],
				"fields": sFields,
				"primary": self._dStruct['primary'],
				"_id": self._dRecord[self._dStruct['primary']]
			}

			# Execute the SQL
			Record_MySQL.Commands.execute(
				self._dStruct['host'],
				sSQL
			)

	@classmethod
	def withTrigger(cls, custom={}):
		"""With Trigger

		Fetches outreach joined with trigger so it can be sorted by date

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
		sSQL = 'SELECT\n' \
				'	`wdo`.`_id`,\n' \
				'	`wdo`.`crm_type`,\n' \
				'	`wdo`.`crm_id`,\n' \
				'	`wdo`.`crm_order`,\n' \
				'	`wdo`.`queue`,\n' \
				'	`wdo`.`reason`,\n' \
				'	`wdo`.`ready`,\n' \
				'	CAST(`wdt`.`_created` as date) as `triggered`\n' \
				'FROM `%(db)s`.`%(table)s` as `wdo`\n' \
				'LEFT JOIN `%(db)s`.`welldyne_trigger` as `wdt` USING (`crm_type`, `crm_id`, `crm_order`)\n' \
				'ORDER BY `triggered` ASC' % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Execute and return the select
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)

# OutboundSent class
class OutboundSent(Record_MySQL.Record):
	"""OutboundSent

	Represents an outbound failure from Welldyne that we've reprocessed
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
				Tree.fromFile('definitions/welldyne/outbound_sent.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def fromFillError(cls, error, custom={}):
		"""From Fill Error

		Creates a sent record from something that previously failed

		Arguments:
			error (PharmacyFillError): The error that re-processed successfully
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate the necessary fields
		sFields = '`crm_type`, `crm_id`, `crm_order`'

		# Generate SQL
		sSQL = "INSERT INTO `%(db)s`.`%(table)s` (`%(primary)s`, %(fields)s)\n" \
				"VALUES (UUID(), '%(crm_type)s', '%(crm_id)s', '%(crm_order)s')\n" \
				"ON DUPLICATE KEY UPDATE `attempts` = `attempts` + 1 " % {
			"db": self._dStruct['db'],
			"table": self._dStruct['table'],
			"fields": lFields,
			"primary": self._dStruct['primary'],
			"crm_type": error['crm_type'],
			"crm_id": error['crm_id'],
			"crm_order": error['crm_order']
		}

		# Execute the SQL
		Record_MySQL.Commands.execute(
			self._dStruct['host'],
			sSQL
		)

# RxNumber class
class RxNumber(Record_MySQL.Record):
	"""RxNumber

	Represents a prescription number on WellDyne's side
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
				Tree.fromFile('definitions/welldyne/rx_number.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Trigger class
class Trigger(Record_MySQL.Record):
	"""Trigger

	Represents an order with a customer that's been triggered to WellDyne
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
				Tree.fromFile('definitions/welldyne/trigger.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def vsShipped(cls, custom={}):
		"""Vs Shipped

		Fetches the latest triggers and gives the count vs how many have been
		shipped

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
		sSQL = 'SELECT COUNT(*) as `count`\n' \
				'FROM `%(db)s`.`%(table)s`\n' \
				'UNION\n' \
				'SELECT COUNT(*) as `count`\n' \
				'FROM `%(db)s`.`%(table)s`\n' \
				'WHERE `shipped` IS NOT NULL' % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}

		# Execute and return the select
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.COLUMN
		)

	@classmethod
	def withOutreachEligibility(cls, crm_type, crm_id, custom={}):
		"""With Outreach & Eligibility

		Fetches the latest trigger associated with the customer, including any
		possible outreach and eligibility data

		Arguments:
			crm_type (str): The type of CRM the customer belongs to
			crm_id (str): The ID of the customer to look up
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict[]
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT\n" \
				"	`wdt`.`_id` as `_id`,\n" \
				"	`wdt`.`crm_type` as `crm_type`,\n" \
				"	`wdt`.`crm_id` as `crm_id`,\n" \
				"	`wdt`.`crm_order` as `crm_order`,\n" \
				"	`wdt`.`rx_id` as `rx_id`,\n" \
				"	`wdt`.`medication` as `medication`,\n" \
				"	`wdt`.`_created` as `triggered`,\n" \
				"	`wdt`.`type` as `type`,\n" \
				"	`wdt`.`opened` as `opened`,\n" \
				"	`wdt`.`shipped` as `shipped`,\n" \
				"	`wdt`.`raw` as `raw`,\n" \
				"	`wdo`.`queue` as `outbound_queue`,\n" \
				"	`wdo`.`reason` as `outbound_reason`,\n" \
				"	`wda`.`type` as `adhoc_type`\n" \
				"FROM `%(db)s`.`%(table)s` as `wdt`\n" \
				"LEFT JOIN `%(db)s`.`welldyne_outbound` as `wdo` USING (`crm_type`, `crm_id`, `crm_order`)\n" \
				"LEFT JOIN `%(db)s`.`welldyne_adhoc` as `wda` ON `wdt`.`_id` = `wda`.`trigger_id`\n" \
				"WHERE `wdt`.`crm_type` = '%(crm_type)s'\n" \
				"AND `wdt`.`crm_id` = '%(crm_id)s'\n" \
				"ORDER BY `triggered` DESC" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"crm_type": crm_type,
			"crm_id": crm_id
		}

		# Execute and return the select
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ALL
		)
