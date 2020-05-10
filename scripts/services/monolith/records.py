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

# SQL files
with open('./services/monolith/sql/unclaimed.sql') as oF:
	sUnclaimedSQL = oF.read()
with open('./services/monolith/sql/claimed.sql') as oF:
	sClaimedSQL = oF.read()
with open('./services/monolith/sql/claimed_new.sql') as oF:
	sClaimedNewSQL = oF.read()
with open('./services/monolith/sql/conversation.sql') as oF:
	sConversationSQL = oF.read()
with open('./services/monolith/sql/msg_phone_update.sql') as oF:
	sMsgPhoneUpdateSQL = oF.read()
with open('./services/monolith/sql/landing.sql') as oF:
	sLandingSQL = oF.read()

# CustomerClaimed structure and config
_mdCustomerClaimedConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/customer_claimed.json'),
	'mysql'
)

# CustomerCommunication structure and config
_mdCustomerCommunicationConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/customer_communication.json'),
	'mysql'
)

# CustomerMsgPhone structure and config
_mdCustomerMsgPhoneConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/customer_msg_phone.json'),
	'mysql'
)

# DsPatient structure and config
_mdDsPatientConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/ds_patient.json'),
	'mysql'
)

# Forgot structure and config
_mdForgotConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/forgot.json'),
	'mysql'
)

# KtCustomer structure and config
_mdKtCustomerConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/kt_customer.json'),
	'mysql'
)

# KtOrder structure and config
_mdKtOrderConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/kt_order.json'),
	'mysql'
)

# SMSStop structure and config
_mdSMSStopConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/sms_stop.json'),
	'mysql'
)

# TfAnswer structure and config
_mdTfAnswerConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/tf_answer.json'),
	'mysql'
)

# TfLanding structure and config
_mdTfLandingConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/tf_landing.json'),
	'mysql'
)

# TfQuestion structure and config
_mdTfQuestionConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/tf_question.json'),
	'mysql'
)

# TfQuestionOption structure and config
_mdTfQuestionOptionConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/tf_question_option.json'),
	'mysql'
)

# User structure and config
_mdUserConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/monolith/user.json'),
	'mysql'
)

# CustomerClaimed class
class CustomerClaimed(Record_MySQL.Record):
	"""CustomerClaimed

	Represents a customer conversation that has been claimed by an agent

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdCustomerClaimedConf

# CustomerCommunication class
class CustomerCommunication(Record_MySQL.Record):
	"""CustomerCommunication

	Represents a message to or from a customer or potential customer

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdCustomerCommunicationConf

	@classmethod
	def newMessages(cls, numbers, ts, custom={}):
		"""New Messages

		Checks for new messages from the given numbers

		Arguments:
			numbers {str[]} -- List of phone numbers to check
			ts {uint} -- Timestamp indicating last check
			custom {dict} -- Custom Host and DB info
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

		# Go through each record
		for d in lRecords:
			if d['type'] == 'Incoming':
				if d['fromPhone'] in dRet: dRet[d['fromPhone']] += 1
				else: dRet[d['fromPhone']] = 1
			elif d['type'] == 'Outgoing':
				if d['toPhone'] in dRet: dRet[d['toPhone']] += 1
				else: dRet[d['toPhone']] = 1

		# Return
		return dRet

	@classmethod
	def thread(cls, number, custom={}):
		"""Thread

		Fetches all the records in or out associated with a phone number in
		chronological order

		Arguments:
			number {str} -- The phone number to look up
			custom {dict} -- Custom Host and DB info
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

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdCustomerMsgPhoneConf

	@classmethod
	def claimed(cls, user, custom={}):
		"""Claimed

		Returns all the conversations the user has claimed

		Arguments:
			user {int} -- The ID of the user
			custom {dict} -- Custom Host and DB info
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
			}
		)

	@classmethod
	def unclaimed(cls, custom={}):
		"""Unclaimed

		Fetches open conversations that have not been claimed by any agent

		Arguments:
			custom {dict} -- Custom Host and DB info
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
			}
		)

	@classmethod
	def addMessage(cls, customerPhone, date, message, custom={}):
		"""Add Message

		Adds an outgoing message to the conversation summary

		Arguments:
			customerPhone {str} -- The number associated with the conversation
			message {str} -- The message to prepend to the conversation
			custom {dict} -- Custom Host and DB info
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
			"message": message,
			"customerPhone": customerPhone
		}

		# Execute the update
		Record_MySQL.Commands.execute(dStruct['host'], sSQL)

# DsPatient class
class DsPatient(Record_MySQL.Record):
	"""DsPatient

	Represents a customer in DoseSpot

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdDsPatientConf

# Forgot class
class Forgot(Record_MySQL.Record):
	"""Forgot

	Represents an attempt to reset a forgotten password

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdForgotConf

# KtCustomer class
class KtCustomer(Record_MySQL.Record):
	"""KtCustomer

	Represents a customer in konnektive

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdKtCustomerConf

# KtOrder class
class KtOrder(Record_MySQL.Record):
	"""KtOrder

	Represents a customer's order in konnektive

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdKtOrderConf

# SMSStop class
class SMSStop(Record_MySQL.Record):
	"""SMSStop

	Represents a customer phone number that should be blocked

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdSMSStopConf

# TfAnswer class
class TfAnswer(Record_MySQL.Record):
	"""TfAnswer

	Represents a customer phone number that should be blocked

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdTfAnswerConf

# TfLanding class
class TfLanding(Record_MySQL.Record):
	"""TfLanding

	Represents a customer phone number that should be blocked

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdTfLandingConf

	@classmethod
	def find(cls, last_name, email, phone, custom={}):
		"""Find

		Attempts to find a landing using customer info

		Arguments:
			last_name {str} -- The last name of the customer
			email {str} -- The email of the customer
			phone {str} -- The phone number of the customer
			custom {dict} -- Custom Host and DB info
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
			Record_MySQL.ESelect.ROW
		)

# TfQuestion class
class TfQuestion(Record_MySQL.Record):
	"""TfQuestion

	Represents a customer phone number that should be blocked

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdTfQuestionConf

# TfQuestionOption class
class TfQuestionOption(Record_MySQL.Record):
	"""TfQuestionOption

	Represents a customer phone number that should be blocked

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdTfQuestionOptionConf

# User class
class User(Record_MySQL.Record):
	"""User

	Represents a Memo user

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdUserConf

	@classmethod
	def passwordStrength(cls, passwd):
		"""Password Strength

		Returns true if a password is secure enough

		Arguments:
			passwd {str} -- The password to check

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
