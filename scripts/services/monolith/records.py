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

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# Custome SQL
sClaimedSQL = ''
sClaimedNewSQL = ''
sConversationSQL = ''
sLandingSQL = ''
sLatestStatusSQL = ''
sMsgPhoneUpdateSQL = ''
sSmpNotes = ''
sNumOfOrdersSQL = ''
sSearchSQL = ''
sTriggerSQL = ''
sUnclaimedSQL = ''
sUnclaimedCountSQL = ''

def init():
	"""Ugly Hack

	Need to find a better way to do this
	"""

	global sClaimedSQL, sClaimedNewSQL, sConversationSQL, sLandingSQL, \
			sLatestStatusSQL, sMsgPhoneUpdateSQL, sSmpNotes, sNumOfOrdersSQL, \
			sSearchSQL, sTriggerSQL, sUnclaimedSQL, sUnclaimedCountSQL

	# SQL files
	with open('./services/monolith/sql/claimed.sql') as oF:
		sClaimedSQL = oF.read()
	with open('./services/monolith/sql/claimed_new.sql') as oF:
		sClaimedNewSQL = oF.read()
	with open('./services/monolith/sql/conversation.sql') as oF:
		sConversationSQL = oF.read()
	with open('./services/monolith/sql/landing.sql') as oF:
		sLandingSQL = oF.read()
	with open('./services/monolith/sql/latest_status.sql') as oF:
		sLatestStatusSQL = oF.read()
	with open('./services/monolith/sql/msg_phone_update.sql') as oF:
		sMsgPhoneUpdateSQL = oF.read()
	with open('./services/monolith/sql/smp_notes.sql') as oF:
		sSmpNotes = oF.read()
	with open('./services/monolith/sql/number_of_orders.sql') as oF:
		sNumOfOrdersSQL = oF.read()
	with open('./services/monolith/sql/search.sql') as oF:
		sSearchSQL = oF.read()
	with open('./services/monolith/sql/trigger.sql') as oF:
		sTriggerSQL = oF.read()
	with open('./services/monolith/sql/unclaimed.sql') as oF:
		sUnclaimedSQL = oF.read()
	with open('./services/monolith/sql/unclaimed_count.sql') as oF:
		sUnclaimedCountSQL = oF.read()

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
				Tree.fromFile('../definitions/monolith/customer_claimed.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

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
				Tree.fromFile('../definitions/monolith/customer_communication.json'),
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
			lNumbers.extend([s, '1%s' % s])

		# Generate SQL
		sSQL = sClaimedNewSQL % {
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
				"number": number
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
				Tree.fromFile('../definitions/monolith/customer_msg_phone.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def addIncoming(cls, customerPhone, date, message, custom={}):
		"""Add Incoming

		Adds an incoming message to the conversation summary

		Arguments:
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

		# Generate SQL
		sSQL = sMsgPhoneUpdateSQL % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"date": date,
			"direction": 'Incoming',
			"message": Record_MySQL.Commands.escape(dStruct['host'], message),
			"customerPhone": customerPhone,
			"hidden": 'N',
			"increment": 'totalIncoming'
		}

		# Execute the update
		Record_MySQL.Commands.execute(dStruct['host'], sSQL)

	@classmethod
	def addOutgoing(cls, customerPhone, date, message, custom={}):
		"""Add Outgoing

		Adds an outgoing message to the conversation summary

		Arguments:
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

		# Generate SQL
		sSQL = sMsgPhoneUpdateSQL % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"date": date,
			"direction": 'Outgoing',
			"message": Record_MySQL.Commands.escape(dStruct['host'], message),
			"customerPhone": customerPhone,
			"hidden": 'Y',
			"increment": 'totalOutGoing'
		}

		# Execute the update
		Record_MySQL.Commands.execute(dStruct['host'], sSQL)

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

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sClaimedSQL % {
				"db": dStruct['db'],
				"user": user
			},
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
			lWhere.append("`customerPhone` LIKE '%%%s%%'" % q['phone'][-10:])
		if 'name' in q and q['name']:
			lWhere.append("`customerName` LIKE '%%%s%%'" % q['name'])
		if 'content' in q and q['content']:
			lWhere.append("`lastMsg` LIKE '%%%s%%'" % q['content'])

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
	def unclaimed(cls, custom={}):
		"""Unclaimed

		Fetches open conversations that have not been claimed by any agent

		Arguments:
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
			sUnclaimedSQL % {
				"db": dStruct['db']
			},
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

		# Fetch and return the data
		return Record_MySQL.Commands.select(
			dStruct['host'],
			sUnclaimedCountSQL % {
				"db": dStruct['db']
			},
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
				Tree.fromFile('../definitions/monolith/ds_patient.json'),
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
				Tree.fromFile('../definitions/monolith/forgot.json'),
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
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""

		# If we haven loaded the config yet
		if not cls._conf:
			cls._conf = Record_MySQL.Record.generateConfig(
				Tree.fromFile('../definitions/monolith/kt_customer.json'),
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
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""

		# If we haven loaded the config yet
		if not cls._conf:
			cls._conf = Record_MySQL.Record.generateConfig(
				Tree.fromFile('../definitions/monolith/kt_order.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

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
				"phone": phone
			},
			Record_MySQL.ESelect.COLUMN
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
				Tree.fromFile('../definitions/monolith/shipping_info.json'),
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
				Tree.fromFile('../definitions/monolith/smp_note.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

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
				Tree.fromFile('../definitions/monolith/smp_order_status.json'),
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
				Tree.fromFile('../definitions/monolith/sms_stop.json'),
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
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""

		# If we haven loaded the config yet
		if not cls._conf:
			cls._conf = Record_MySQL.Record.generateConfig(
				Tree.fromFile('../definitions/monolith/tf_answer.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

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
				Tree.fromFile('../definitions/monolith/tf_landing.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def find(cls, last_name, email, phone, custom={}):
		"""Find

		Attempts to find a landing using customer info

		Arguments:
			last_name (str): The last name of the customer
			email (str): The email of the customer
			phone (str): The phone number of the customer
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			dict
		"""

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Generate SQL
		sSQL = sLandingSQL % {
			"db": dStruct['db'],
			"table": dStruct['table'],
			"lastName": last_name,
			"email": email,
			"phone": phone
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
				Tree.fromFile('../definitions/monolith/tf_question.json'),
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
				Tree.fromFile('../definitions/monolith/tf_question_option.json'),
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
				Tree.fromFile('../definitions/monolith/user.json'),
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

# WdEligibility class
class WdEligibility(Record_MySQL.Record):
	"""WdEligibility

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
				Tree.fromFile('../definitions/monolith/wd_eligibility.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# WdOutreach class
class WdOutreach(Record_MySQL.Record):
	"""WdOutreach

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

# WdTrigger class
class WdTrigger(Record_MySQL.Record):
	"""WdTrigger

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
		sSQL = sTriggerSQL % {
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
