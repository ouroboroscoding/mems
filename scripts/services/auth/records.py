# coding=utf8
""" Auth Records

Handles the record structures for the auth service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-03-29"

# Python imports
from hashlib import sha1
import re

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL, StrHelper

# Forst structure and config
_mdForgotConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/auth/forgot.json'),
	'mysql'
)

# Login structure and config
_mdLoginConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/auth/login.json'),
	'mysql'
)

# Forgot class
class Forgot(Record_MySQL.Record):
	"""Forgot

	Represents a single thrower (aka, user)

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

# Login class
class Login(Record_MySQL.Record):
	"""Login

	Represents a single thrower (aka, user)

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdLoginConf

	@staticmethod
	def passwordHash(passwd):
		"""Password Hash

		Returns a hashed password with a unique salt

		Arguments:
			passwd {str} -- The password to hash

		Returns:
			str
		"""

		# Generate the salt
		sSalt = StrHelper.random(32, '_0x')

		# Generate the hash
		sHash = sha1(sSalt.encode('utf-8') + passwd.encode('utf-8')).hexdigest()

		# Combine the salt and hash and return the new value
		return sSalt[:20] + sHash + sSalt[20:]

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
			re.search('[A-Za-z]+', passwd) == None or \
			re.search('[0-9]+', passwd) == None:

			# Invalid password
			return False

		# Return OK
		return True

	def passwordValidate(self, passwd):
		"""Password Validate

		Validates the given password against the current instance

		Arguments:
			passwd {str} -- The password to validate

		Returns:
			bool
		"""

		# Get the password from the record
		sPasswd = self.fieldGet('passwd')

		# Split the password
		sSalt = sPasswd[:20] + sPasswd[60:]
		sHash = sPasswd[20:60]

		# Return OK if the rehashed password matches
		return sHash == sha1(sSalt.encode('utf-8') + passwd.encode('utf-8')).hexdigest()

	@classmethod
	def search(cls, q):
		"""Search

		Searches for throwers based on alias

		Arguments:
			q string -- The query to search

		Returns:
			list
		"""

		# Get the structure
		dStruct = cls.struct()

		# Generate the SELECT statement
		sSQL = 'SELECT %s FROM `%s`.`%s` ' \
				'WHERE `email` LIKE \'\%%s\%\' ' \
				'OR `phoneNumber` LIKE \'\%%s\%\' ' \
				'OR CONCAT(`firstName`, \' \', `lastName`) LIKE \'\%%s\%\' ' \
				'ORDER BY `firstName`, `lastName`' % (
			dStruct['primary'],
			dStruct['db'],
			dStruct['table'],
			q
		)

		# Fetch any records
		Record_MySQL.Commands.select(dStruct['host'], sSQL, ESelect.COL)
