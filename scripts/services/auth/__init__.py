# coding=utf8
""" Auth Service

Handles all Authorization / Login requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-03-29"

# Python imports
import re
from time import time

# Pip imports
from redis import StrictRedis
from RestOC import Conf, DictHelper, Errors, Services, \
					Sesh, StrHelper, Templates

# Local imports
from shared import Rights

# Service imports
from .records import Forgot, Permission, User

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

class Auth(Services.Service):
	"""Auth Service class

	Service for Authorization, sign in, sign up, etc.

	Extends: shared.Services.Service
	"""

	_install = [Forgot, User, Permission]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Auth
		"""

		# Create a connection to Redis
		self._redis = StrictRedis(**Conf.get(('redis', 'primary'), {
			"host": "localhost",
			"port": 6379,
			"db": 0
		}))

		# Pass the Redis connection to User
		User.redis(self._redis)

	@classmethod
	def install(cls):
		"""Install

		The service's install method, used to setup storage or other one time
		install configurations

		Returns:
			bool
		"""

		# Go through each Record type
		for o in cls._install:

			# Install the table
			if not o.tableCreate():
				print("Failed to create `%s` table" % o.tableName())

	def passwdForgot_create(self, data):
		"""Password Forgot (Generate)

		Creates the key that will be used to allow a user to change their
		password if they forgot it

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'url'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the user by email
		dUser = User.filter({"email": data['email']}, raw=['_id', 'locale'], limit=1)
		if not dUser:
			return Services.Effect(False)

		# Look for a forgot record by user id
		oForgot = Forgot.get(dUser['_id'])

		# Is there already a key in the user?
		if oForgot and 'regenerate' not in data:

			# Is it not expired?
			if oForgot['expires'] > int(time()):
				return Services.Effect(True)

		# Upsert the forgot record with a timestamp (for expiry) and the key
		sKey = StrHelper.random(32, '_0x')
		oForgot = Forgot({
			"_user": dUser['_id'],
			"expires": int(time()) + Conf.get(("services", "auth", "forgot_expire"), 600),
			"key": sKey
		})
		if not oForgot.create(conflict="replace"):
			return Services.Effect(error=1100)

		# Forgot email template variables
		dTpl = {
			"key": sKey,
			"url": "%s%s" % (
				data['url'],
				sKey
			)
		}

		# Email the user the key
		oEffect = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/forgot.html', dTpl, dUser['locale']),
			"subject": Templates.generate('email/forgot_subject.txt', {}, dUser['locale']),
			"to": data['email'],
		})
		if oEffect.errorExists():
			return oEffect

		# Return OK
		return Services.Effect(True)

	def passwdForgot_update(self, data):
		"""Password Forgot (Change Password)

		Validates the key and changes the password to the given value

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['passwd', 'key'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the forgot by the key
		oForgot = Forgot.filter({"key": data['key']}, limit=1)
		if not oForgot:
			return Services.Effect(error=1203) # Don't let people know if the key exists or not

		# Check if the key has expired
		if oForgot['expires'] <= int(time()):
			return Services.Effect(error=1203)

		# Make sure the new password is strong enough
		if not User.passwordStrength(data['passwd']):
			return Services.Effect(error=1204)

		# Find the User
		oUser = User.get(oForgot['_user'])
		if not oUser:
			return Services.Effect(error=1203)

		# Store the new password and update
		oUser['passwd'] = User.passwordHash(data['passwd'])
		oUser.save(changes=False)

		# Delete the forgot record
		oForgot.delete()

		# Return OK
		return Services.Effect(True)

	def permissions_read(self, data, sesh):
		"""Permissions

		Returns all permissions associated with a user

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = self.verify_read({
			"name": "permissions",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['user_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Fetch the User
		dUser = User.cache(data['user_id'])

		# If there's no such user
		if not dUser:
			return Services.Effect(error=(1104, 'User not found'))

		# Return all permissions
		return Services.Effect(dUser['permissions'])

	def permissions_update(self, data, sesh):
		"""Permissions Update

		Updates all permissions associated with a specific user

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = self.verify_read({
			"name": "permissions",
			"right": Rights.UPDATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['user', 'permissions'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Get the user's current permissions
		oUser = User.get(data['user'])
		dOldPermissions = oUser.permissions()

		# Init the new permissions
		dPermissions = {}

		# Validate and store the new permissions
		lRecords = []
		for d in data['permissions']:
			lErrors = []
			try:
				dPermissions[d['name']] = d['rights']
				lRecords.append(Permission({
					"user": data['user'],
					"name": d['name'],
					"rights": d['rights']
				}))
			except ValueError as e:
				lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Effect(error=(1001, lErrors))

		# Delete all the existing permissions if there are any
		if dOldPermissions:
			Permission.deleteGet(data['user_id'], 'user_id')

		# Create the new permissions
		Permission.createMany(lRecords)

		# Get and store the changes
		dChanges = {"user": sesh['user_id']}
		if dOldPermissions and dPermissions:
			dChanges['permissions'] = self.generateChanges(dOldPermissions, dPermissions)
		elif dPermissions:
			dChanges['permissions'] = {"old": None, "new": "inserted"}
		else:
			dChanges['permissions'] = {"old": dOldPermissions, "new": None}
		User.addChanges(data['user'], dChanges)

		# Return OK
		return Services.Effect(True)

	def search_read(self, data, sesh):
		"""Search

		Looks up users by alias

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['q'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Fetch the IDs
		lRecords = User.search(data['q'])

		# If we got something, fetch the records from the cache
		if not lRecords:
			lRecords = User.cache(lRecords, raw=True)

		# Run a search and return the results
		return Services.Effect(lRecords)

	def session_read(self, data, sesh):
		"""Session

		Returns the ID of the user logged into the current session

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return Services.Effect({
			"user_id": sesh['user_id']
		})

	def signin_create(self, data):
		"""Signin

		Signs a user into the system

		Arguments:
			data {dict} -- The data passed to the request

		Returns:
			Result
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'passwd'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the user by alias
		oUser = User.filter({"email": data['email']}, limit=1)
		if not oUser:
			return Services.Effect(error=1201)

		# Validate the password
		if not oUser.passwordValidate(data['passwd']):
			return Services.Effect(error=1201)

		# Create a new session
		oSesh = Sesh.create()

		# Store the user ID and information in it
		oSesh['user_id'] = oUser['_id']

		# Save the session
		oSesh.save()

		# Return the session ID and primary user data
		return Services.Effect({
			"session": oSesh.id(),
			"user_id": oSesh['user_id']
		})

	def signout_create(self, data, sesh):
		"""Signout

		Called to sign out a user and destroy their session

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the user

		Returns:
			Services.Effect
		"""

		# Close the session so it can no longer be found/used
		sesh.close()

		# Return OK
		return Services.Effect(True)

	def user_create(self, data, sesh):
		"""User Create

		Creates a new user

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the user

		Returns:
			Effect
		"""

		# Make sure the user has the proper permission to do this
		oEff = self.verify_read({
			"name": "user",
			"right": Rights.CREATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['email', 'passwd'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Check if a user with that email already exists
		if User.exists(data['email'], 'email'):
			return Services.Effect(error=1200)

		# Check the password strength
		if not User.passwordStrength(data['passwd']):
			return Services.Effect(error=1204)

		# Hash the password
		data['passwd'] = User.passwordHash(data['passwd'])

		# Validate by creating a Record instance
		try:
			oUser = User(data)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the row and return the result
		return Services.Effect(
			oUser.create(changes={"user": sesh['user_id']})
		)

	def user_read(self, data, sesh):
		"""User Read

		Fetches an existing user and returns their data

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the user

		Returns:
			Effect
		"""

		# If there's an ID, check permissions
		if '_id' in data:

			# Make sure the user has the proper permission to do this
			oEff = self.verify_read({
				"name": "user",
				"right": Rights.READ
			}, sesh)
			if not oEff.data:
				return Services.Effect(error=Rights.INVALID)

		# Else, assume the signed in user's Record
		else:
			data['_id'] = sesh['user_id']

		# Fetch it from the cache
		dUser = User.cache(data['_id'], raw=True)

		# If it doesn't exist
		if not dUser:
			return Services.Effect(error=1104)

		# Remove the passwd field
		del dUser['passwd']

		# Return the user data
		return Services.Effect(dUser)

	def user_update(self, data, sesh):
		"""User Update

		Updates an existing user

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the user

		Returns:
			Effect
		"""

		# If there's an ID, check permissions
		if '_id' in data or data['_id'] != sesh['user_id']:

			# Make sure the user has the proper permission to do this
			oEff = self.verify_read({
				"name": "user",
				"right": Rights.UPDATE
			}, sesh)
			if not oEff.data:
				return Services.Effect(error=Rights.INVALID)

		# Else, assume the signed in user's Record
		else:
			data['_id'] = sesh['user_id']

		# Fetch it from the cache
		oUser = User.cache(data['_id'])

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']


	def userEmail_update(self, data, sesh):
		"""User Email

		Changes the email for the current signed in user

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the user

		Returns:
			Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'email_passwd'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Find the user
		oUser = User.get(sesh['user_id'])
		if not oUser:
			return Services.Effect(error=1104)

		# Validate the password
		if not oUser.passwordValidate(data['email_passwd']):
			return Services.Effect(error=(1001, [('email_passwd', 'invalid')]))

		# Make sure the email is valid structurally
		if not _emailRegex.match(data['email']):
			return Services.Effect(error=(1001, [('email', 'invalid')]))

		# Look for someone else with that email
		dUser = User.filter({"email": data['email']}, raw=['_id'])
		if dUser:
			return Services.Effect(error=(1206, data['email']))

		# Update the email and verified fields
		try:
			oUser['email'] = data['email']
			oUser['verified'] = StrHelper.random(32, '_0x')
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Update the user
		oUser.save(changes={"user":sesh['user_id']})

		# Return OK
		return Services.Effect(True)

	def userPasswd_update(self, data, sesh):
		"""User Password

		Changes the password for the current signed in user

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the user

		Returns:
			Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['passwd', 'new_passwd'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Find the user
		oUser = User.get(sesh['user']['_id'])
		if not oUser:
			return Services.Effect(error=1104)

		# Validate the password
		if not oUser.passwordValidate(data['passwd']):
			return Services.Effect(error=(1001, [('passwd', 'invalid')]))

		# Make sure the new password is strong enough
		if not User.passwordStrength(data['new_passwd']):
			return Services.Effect(error=1204)

		# Set the new password and save
		oUser['passwd'] = User.passwordHash(data['new_passwd'])
		oUser.save(changes={"user":sesh['user']['_id']})

		# Return OK
		return Services.Effect(True)

	def verify_read(self, data, sesh):
		"""Verify

		Checks the user currently in the session has access to the requested
		permission

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the user

		Returns:
			Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['name', 'right'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Find the user
		oUser = User.cache(sesh['user_id'])

		# Fetch the permissions from the user instance
		dPermissions = oUser.permissions()

		# If the permission doesn't exist at all
		if not dPermissions or data['name'] not in dPermissions:
			return Services.Effect(False)

		# If the permission exists but doesn't contain the proper right
		if not dPermissions[data['name']] & data['right']:
			return Services.Effect(False)

		# Seems ok
		return Services.Effect(True)
