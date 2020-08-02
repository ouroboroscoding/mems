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
				Tree.fromFile('../definitions/welldyne/adhoc.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def sent(cls, _id, custom={}):
		"""Sent

		Moves the record to the sent table

		Arguments:
			_id (str): The ID of the record to move
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Get the fields in the table without the _created
		lFields = ['`%s`' % s for s in dStruct['tree'].keys() if s != '_created']

		# Generate SQL
		sSQL = "INSERT INTO `%(db)s`.`%(table)s` (%(fields)s) " \
				"SELECT %(fields)s FROM `%(db)s`.`%(table)s_sent` " \
				"WHERE `%(primary)s` = '%(_id)s'; " \
				"DELETE FROM `%(db)s`.`%(table)s` " \
				"WHERE `%(primary)s` = '%(_id)s'" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"fields": lFields,
			"primary": dStruct['primary'],
			"_id": _id
		}

		print(sSQL)

		# Execute the SQL
		Record_MySQL.Commands.execute(
			dStruct['host'],
			sSQL
		)

# AdHocSent class
class AdHocSent(Record_MySQL.Record):
	"""AdHocSent

	Represents an adhoc entry that has been sent to WellDyne
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
				Tree.fromFile('../definitions/welldyne/adhoc_sent.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

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
				Tree.fromFile('../definitions/monolith/wd_eligibility.json'),
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
				"WHERE `wde`.`memberThru` != '0000-00-00 00:00:00'\n" \
				"LIMIT 100" % {
			"db": dStruct['db'],
			"table": dStruct['table']
		}
		print(sSQL)

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
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""

		# If we haven loaded the config yet
		if not cls._conf:
			cls._conf = Record_MySQL.Record.generateConfig(
				Tree.fromFile('../definitions/welldyne/outbound.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def sent(cls, _id, custom={}):
		"""Sent

		Moves the record to the sent table

		Arguments:
			_id (str): The ID of the record to move
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Get the fields in the table without _created, wd_rx, and ready
		lFields = ['`%s`' % s for s in dStruct['tree'].keys() if s not in ['_created', 'wd_rx', 'ready']]

		# Generate SQL
		sSQL = "INSERT INTO `%(db)s`.`%(table)s` (%(fields)s) " \
				"SELECT %(fields)s FROM `%(db)s`.`%(table)s_sent` " \
				"WHERE `%(primary)s` = '%(_id)s' " \
				"ON DUPLICATE KEY UPDATE `count` = VALUE(`count`) + 1; " \
				"DELETE FROM `%(db)s`.`%(table)s` " \
				"WHERE `%(primary)s` = '%(_id)s'" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"fields": lFields,
			"primary": dStruct['primary'],
			"_id": _id
		}

		print(sSQL)

		# Execute the SQL
		Record_MySQL.Commands.execute(
			dStruct['host'],
			sSQL
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
				Tree.fromFile('../definitions/welldyne/outbound_sent.json'),
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
				Tree.fromFile('../definitions/welldyne/trigger.json'),
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
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = "SELECT\n" \
				"	`wdt`.`crm_type` as `crm_type`,\n" \
				"	`wdt`.`crm_id` as `crm_id`,\n" \
				"	`wdt`.`triggered` as `triggered`,\n" \
				"	`wdt`.`opened` as `opened`,\n" \
				"	`wdt`.`shipped` as `shipped`,\n" \
				"	`wdo`.`queue` as `outreachQueue`,\n" \
				"	`wdo`.`reason` as `outreachReason`,\n" \
				"	`wde`.`memberSince` as `eligSince`,\n" \
				"	`wde`.`memberThru` as `eligThru`,\n" \
				"	`wda`.`type` as `adhocType`\n" \
				"FROM `%(db)s`.`%(table)s` as `wdt`\n" \
				"LEFT JOIN `%(db)s`.`welldyne_outreach` as `wdo` ON (`crm_type`, `crm_id`)\n" \
				"LEFT JOIN `%(db)s`.`welldyne_eligibility` as `wde` ON (`crm_type`, `crm_id`)\n" \
				"LEFT JOIN `%(db)s`.`welldyne_adhoc` as `wda` ON (`crm_type`, `crm_id`)\n" \
				"WHERE `wdt`.`crm_type` = '%(crm_type)s'\n" \
				"AND `wdt`.`crm_id` = '%(crm_id)s'" % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"crm_type": crm_type,
			"crm_id": crm_id
		}

		# Execute and return the select
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sSQL,
			Record_MySQL.ESelect.ROW
		)















# OldAdHoc class
class OldAdHoc(Record_MySQL.Record):
	"""OldAdHoc

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
				Tree.fromFile('../definitions/monolith/wd_adhoc.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# OldOutreach class
class OldOutreach(Record_MySQL.Record):
	"""OldOutreach

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
				Tree.fromFile('../definitions/monolith/wd_outreach.json'),
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

# OldTrigger class
class OldTrigger(Record_MySQL.Record):
	"""OldTrigger

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
				Tree.fromFile('../definitions/monolith/wd_trigger.json'),
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
