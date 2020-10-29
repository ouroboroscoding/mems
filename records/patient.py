# coding=utf8
""" Patient Records

Handles the record structures for the patient service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-06-27"

# Python imports
import copy
from hashlib import sha1
import re

# Pip imports
from FormatOC import Tree
from RestOC import Conf, JSON, Record_MySQL, StrHelper

class Account(Record_MySQL.Record):
	"""Account

	Represents a single patient in the system
	"""

	_conf = None
	"""Configuration"""

	_redis = None
	"""Redis

	Holds a connection to the Redis db
	"""

	@classmethod
	def cache(cls, _id, raw=False):
		"""Cache

		Fetches the Users from the cache and returns them

		Arguments:
			_id (str|str[]): The ID(s) to fetch
			raw (bool): Return raw records or Users

		Returns:
			Account|Account[]|dict|dict[]
		"""

		# If we got a single ID
		if isinstance(_id, str):

			# Fetch a single key
			sAccount = cls._redis.get('patient:%s' % _id)

			# If we have a record
			if sAccount:

				# Decode it
				dAccount = JSON.decode(sAccount);

			else:

				# Fetch the record from the DB
				dAccount = cls.get(_id, raw=True)

				# Store it in the cache
				cls._redis.set('patient:%s' % _id, JSON.encode(dAccount))

			# If we don't have a record
			if not dAccount:
				return None

			# If we want raw
			if raw:
				return dAccount

			# Return an instance
			return cls(dAccount)

		# Else, fetch multiple
		else:

			# Init the return
			lRet = []

			# Fetch multiple keys
			lAccounts = cls._redis.mget(["patient:%s" % k for k in _id])

			# Go through each one
			for i in range(len(_id)):

				# If we have a record
				if lAccounts[i]:

					# Decode it
					lAccounts[i] = JSON.decode(lAccounts[i])

				else:

					# Fetch the record from the DB
					lAccounts[i] = cls.get(_id[i], raw=True)

					# Store it in the cache
					cls._redis.set('patient:%s' % _id[i], JSON.encode(lAccounts[i]))

			# If we want raw
			if raw:
				return lAccounts

			# Return instances
			return [d and cls(d) or None for d in lAccounts]

	@classmethod
	def cacheClear(cls, _id):
		"""Cache Clear

		Removes a user from the cache

		Arguments:
			_id (str): The ID of the user to remove

		Returns:
			None
		"""

		# Delete the key in Redis
		cls._redis.delete('patient:%s' % _id)

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
				Tree.fromFile('definitions/patient/account.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@staticmethod
	def passwordHash(passwd):
		"""Password Hash

		Returns a hashed password with a unique salt

		Arguments:
			passwd (str): The password to hash

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
			passwd (str): The password to check

		Returns:
			bool
		"""

		# If we don't have enough or the right chars
		if 8 > len(passwd) or \
			re.search('[A-Z]+', passwd) == None or \
			re.search('[a-z]+', passwd) == None or \
			re.search('[0-9]+', passwd) == None:

			# Invalid password
			return False

		# Return OK
		return True

	def passwordValidate(self, passwd):
		"""Password Validate

		Validates the given password against the current instance

		Arguments:
			passwd (str): The password to validate

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
	def redis(cls, redis):
		"""Redis

		Stores the Redis connection to be used to fetch and store Users

		Arguments:
			redis (StrictRedis): A Redis instance

		Returns:
			None
		"""
		cls._redis = redis

# AccountSetup class
class AccountSetup(Record_MySQL.Record):
	"""AccountSetup

	Represents the initial starting of a patient user record
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
				Tree.fromFile('definitions/patient/account_setup.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# AccountSetupAttempt class
class AccountSetupAttempt(Record_MySQL.Record):
	"""AccountSetupAttempt

	Represents a failed attempt to setup a patient account
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
				Tree.fromFile('definitions/patient/account_setup_attempt.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Activity class
class Activity(Record_MySQL.Record):
	"""Activity

	Represents an action by a patient
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
				Tree.fromFile('definitions/patient/activity.json'),
				'mysql'
			)

		# Return the config
		return cls._conf


# Verify class
class Verify(Record_MySQL.Record):
	"""Verify

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
				Tree.fromFile('definitions/patient/verify.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
