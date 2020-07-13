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
import copy
from hashlib import sha1
import re

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL, StrHelper
from shared import JSON

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
				Tree.fromFile('../definitions/auth/forgot.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# Permission class
class Permission(Record_MySQL.Record):
	"""Permission

	Represents a single permission record associated with a user
	"""

	_conf = None
	"""Configuration"""

	_redis = None
	"""Redis

	Holds a connection to the Redis db
	"""

	@classmethod
	def byUser(cls, _id):
		"""By User

		Fetches the permissions as a name => rights/idents dict by user._id

		Arguments:
			_id (str): The ID of the User

		Returns:
			dict
		"""

		# Generate a dict from the name and rights
		return {
			d['name']: {
				"rights": d['rights'],
				"idents": d['idents'] is not None and d['idents'].split(',') or None
			}
			for d in cls.filter({"user": _id}, raw=['name', 'rights', 'idents'])
		}

	@classmethod
	def cache(cls, _id):
		"""Cache

		Fetches the Permissions for one user from the cache and returns them

		Arguments:
			_id (str): The User ID(s) to fetch by

		Returns:
			dict
		"""

		# Fetch a single key
		sPermission = cls._redis.get('perms:%s' % _id)

		# If we have a record
		if sPermission:

			# Decode it
			dPermission = JSON.decode(sPermission);

		else:

			# Fetch the records from the DB
			dPermission = Permission.byUser(_id)

			# Store it in the cache
			cls._redis.set('perms:%s' % _id, JSON.encode(dPermission))

		# If we don't have a record
		if not dPermission:
			return []

		# Return the permissions
		return dPermission

	@classmethod
	def cacheClear(cls, _id):
		"""Cache Clear

		Removes permissions for a user from the cache

		Arguments:
			_id (str): The ID of the user whose permissions we want to clear

		Returns:
			None
		"""

		# Delete the key in Redis
		cls._redis.delete('perms:%s' % _id)

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
				Tree.fromFile('../definitions/auth/permission.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

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

# User class
class User(Record_MySQL.Record):
	"""User

	Represents a single user in the micro services system
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
			User|User[]|dict|dict[]
		"""

		# If we got a single ID
		if isinstance(_id, str):

			# Fetch a single key
			sUser = cls._redis.get('user:%s' % _id)

			# If we have a record
			if sUser:

				# Decode it
				dUser = JSON.decode(sUser);

			else:

				# Fetch the record from the DB
				dUser = cls.get(_id, raw=True)

				# Store it in the cache
				cls._redis.set('user:%s' % _id, JSON.encode(dUser))

			# If we don't have a record
			if not dUser:
				return None

			# If we want raw
			if raw:
				return dUser

			# Return an instance
			return cls(dUser)

		# Else, fetch multiple
		else:

			# Init the return
			lRet = []

			# Fetch multiple keys
			lUsers = cls._redis.mget(["user:%s" % k for k in _id])

			# Go through each one
			for i in range(len(_id)):

				# If we have a record
				if lUsers[i]:

					# Decode it
					lUsers[i] = JSON.decode(lUsers[i])

				else:

					# Fetch the record from the DB
					lUsers[i] = cls.get(_id[i], raw=True)

					# Store it in the cache
					cls._redis.set('user:%s' % _id[i], JSON.encode(lUsers[i]))

			# If we want raw
			if raw:
				return lUsers

			# Return instances
			return [d and cls(d) or None for d in lUsers]

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
		cls._redis.delete('user:%s' % _id)

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
				Tree.fromFile('../definitions/auth/user.json'),
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
		sSQL = 'SELECT `%(id)s` FROM `%(db)s`.`%(table)s` ' \
				'WHERE `email` LIKE \'%%%(q)s%%\' ' \
				'OR `phoneNumber` LIKE \'%%%(q)s%%\' ' \
				'OR CONCAT(`firstName`, \' \', `lastName`) LIKE \'%%%(q)s%%\' ' \
				'ORDER BY `firstName`, `lastName`' % {
			"id": dStruct['primary'],
			"db": dStruct['db'],
			"table": dStruct['table'],
			"q": q
		}

		# Fetch any records
		return Record_MySQL.Commands.select(dStruct['host'], sSQL, Record_MySQL.ESelect.COLUMN)

class UserPatient(Record_MySQL.Record):
	"""UserPatient

	Represents a single user in the CRM system
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
			UserPatient|UserPatient[]|dict|dict[]
		"""

		# If we got a single ID
		if isinstance(_id, str):

			# Fetch a single key
			sUserPatient = cls._redis.get('user:%s' % _id)

			# If we have a record
			if sUserPatient:

				# Decode it
				dUserPatient = JSON.decode(sUserPatient);

			else:

				# Fetch the record from the DB
				dUserPatient = cls.get(_id, raw=True)

				# Store it in the cache
				cls._redis.set('user:%s' % _id, JSON.encode(dUserPatient))

			# If we don't have a record
			if not dUserPatient:
				return None

			# If we want raw
			if raw:
				return dUserPatient

			# Return an instance
			return cls(dUserPatient)

		# Else, fetch multiple
		else:

			# Init the return
			lRet = []

			# Fetch multiple keys
			lUserPatients = cls._redis.mget(["user:%s" % k for k in _id])

			# Go through each one
			for i in range(len(_id)):

				# If we have a record
				if lUserPatients[i]:

					# Decode it
					lUserPatients[i] = JSON.decode(lUserPatients[i])

				else:

					# Fetch the record from the DB
					lUserPatients[i] = cls.get(_id[i], raw=True)

					# Store it in the cache
					cls._redis.set('user:%s' % _id[i], JSON.encode(lUserPatients[i]))

			# If we want raw
			if raw:
				return lUserPatients

			# Return instances
			return [d and cls(d) or None for d in lUserPatients]

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
		cls._redis.delete('user:%s' % _id)

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
				Tree.fromFile('../definitions/auth/user_patient.json'),
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

# UserPatientSetup class
class UserPatientSetup(Record_MySQL.Record):
	"""UserPatientSetup

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
				Tree.fromFile('../definitions/auth/user_patient_setup.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
