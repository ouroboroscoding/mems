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
from shared import JSON

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

# Permission structure and config
_mdPermissionConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/auth/permission.json'),
	'mysql'
)

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

# Login class
class Login(Record_MySQL.Record):
	"""Login

	Represents a single user in the system

	Extends: RestOC.Record_MySQL.Record
	"""

	_redis = None
	"""Redis

	Holds a connection to the Redis db
	"""

	def __init__(self, record):
		"""Constructor

		Overwrites Record_Base constructor to add permissions records

		Arguments:
			record {dict} -- The data associated with the login

		Returns:
			Login
		"""

		# If there's a permissions key
		if 'permissions' in record:
			self.__permissions = record.pop('permissions')

		# Call the parent constructor
		super().__init__(record)

	@classmethod
	def cache(cls, _id, raw=False):
		"""Cache

		Fetches the Logins from the cache and returns them

		Arguments:
			_id {str|str[]} -- The ID(s) to fetch
			raw {bool} -- Return raw records or Logins

		Returns:
			Login|Login[]|dict|dict[]
		"""

		# If we got a single ID
		if isinstance(_id, str):

			# Fetch a single key
			dLogin = cls._redis.get('login:%s' % _id)

			# If we didn't get the key
			if not dLogin:

				# Fetch the record from the DB
				dLogin = cls.get(_id, raw=True)

				# Fetch and store the permissions
				dLogin['permissions'] = Permission.byLogin(_id)

				# Store it in the cache
				cls._redis.set(_id, JSON.encode(dLogin))

			# If we still don't have a record
			if not dLogin:
				return None

			# If we want raw
			if raw:
				return dLogin

			# Return an instance
			return cls(dLogin)

		# Else, fetch multiple
		else:

			# Init the return
			lRet = []

			# Fetch multiple keys
			lLogins = cls._regis.mget(["login:%s" % k for k in _id])

			# Go through each one
			for i in range(len(_id)):

				# If we have a record
				if lLogins[i]:

					# Decode it
					lLogins[i] = JSON.decode(lLogins[i])

				else:

					# Fetch the record from the DB
					lLogins[i] = cls.get(_id, raw=True)

					# Fetch and store the permissions
					lLogins[i]['permissions'] = Permission.byLogin(_id)

					# Store it in the cache
					cls._redis.set(_id, JSON.encode(lLogins[i]))

			# If we want raw
			if raw:
				return lLogins

			# Return instances
			return [d and cls(d) or None for d in lLogins]

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
	def redis(cls, redis):
		"""Redis

		Stores the Redis connection to be used to fetch and store Logins

		Arguments:
			redis {StrictRedis} -- A Redis instance

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

# Permission class
class Permission(Record_MySQL.Record):
	"""Permission

	Represents a single permission record associated with a login

	Extends: RestOC.Record_MySQL.Record
	"""

	READ	= 0x01
	UPDATE	= 0x02
	CREATE	= 0x04
	DELETE	= 0x08
	ALL		= 0x0F
	"""Right Types

	The bits for individual CRUD rights
	"""

	def byLogin(cls, _id):
		"""By Login

		Fetches the permissions as a name => rights dict by login.id

		Arguments:
			_id {str} -- The ID of the Login

		Returns:
			dict
		"""

		# Generate a dict from the name and rights
		return {
			d['name']:d['rights']
			for d in cls.filter({"login_id": _id}, raw=['name', 'rights'])
		}

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdPermissionConf
