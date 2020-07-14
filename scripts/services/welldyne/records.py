# coding=utf8
""" WellDyne Records

Handles the record structures for the welldyne service
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

	Represents a customer in the adhoc table
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
				Tree.fromFile('../definitions/welldyne/adhoc.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Eligibility class
class Eligibility(Record_MySQL.Record):
	"""Eligibility

	Represents a customer's WellDyneRx eligibility
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
				Tree.fromFile('../definitions/welldyne/eligibility.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Outreach class
class Outreach(Record_MySQL.Record):
	"""Outreach

	Represents a customer's last outreach issue with WellDyneRx
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
				Tree.fromFile('../definitions/welldyne/outreach.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

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
				'	`wdo`.`id`,\n' \
				'	`wdo`.`customerId`,\n' \
				'	`wdo`.`queue`,\n' \
				'	`wdo`.`reason`,\n' \
				'	`wdo`.`user`,\n' \
				'	`wdo`.`ready`,\n' \
				'	CAST(`wdt`.`triggered` as date) as `triggered`\n' \
				'FROM `%(db)s`.`%(table)s` as `wdo`\n' \
				'LEFT JOIN `%(db)s`.`wd_trigger` as `wdt` ON `wdo`.`customerId` = `wdt`.`customerId`\n' \
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

# Trigger class
class Trigger(Record_MySQL.Record):
	"""Trigger

	Represents a customer's last WellDyneRx trigger
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
				Tree.fromFile('../definitions/welldyne/trigger.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def withOutreachEligibility(cls, customer_id, custom={}):
		"""With Outreach & Eligibility

		Fetches the latest trigger associated with the customer, including any
		possible outreach and eligibility data

		Arguments:
			customer_id (int): The ID of the customer to look up
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
				'	`wdt`.`customerId` as `customerId`,\n' \
				'	`wdt`.`triggered` as `triggered`,\n' \
				'	`wdt`.`opened` as `opened`,\n' \
				'	`wdt`.`shipped` as `shipped`,\n' \
				'	`wdo`.`queue` as `outreachQueue`,\n' \
				'	`wdo`.`reason` as `outreachReason`,\n' \
				'	`wde`.`memberSince` as `eligSince`,\n' \
				'	`wde`.`memberThru` as `eligThru`,\n' \
				'	`wda`.`type` as `adhocType`\n' \
				'FROM `%(db)s`.`%(table)s` as `wdt`\n' \
				'LEFT JOIN `%(db)s`.`wd_outreach` as `wdo` ON `wdt`.`customerId` = `wdo`.`customerId`\n' \
				'LEFT JOIN `%(db)s`.`wd_eligibility` as `wde` on `wdt`.`customerId` = `wde`.`customerId`\n' \
				'LEFT JOIN `%(db)s`.`wd_adhoc` as `wda` on `wdt`.`customerId` = `wda`.`customerId`\n' \
				'WHERE `wdt`.`customerId` = \'%(customerId)s\'' % {
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
