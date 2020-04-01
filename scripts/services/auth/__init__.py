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

# Service imports
from .records import Forgot, Login

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

class Auth(Services.Service):
	"""Auth Service class

	Service for Authorization, sign in, sign up, etc.

	Extends: shared.Services.Service
	"""

	_install = [Forgot, Login, Permission]
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

		# Pass the Redis connection to Login
		Login.redis(self._redis)

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

		# Look for the login by email
		dLogin = Login.filter({"email": data['email']}, raw=['_id', 'locale'], limit=1)
		if not dLogin:
			return Services.Effect(False)

		# Look for a forgot record by login id
		oForgot = Forgot.get(dLogin['_id'])

		# Is there already a key in the login?
		if oForgot and 'regenerate' not in data:

			# Is it not expired?
			if oForgot['expires'] > int(time()):
				return Services.Effect(True)

		# Upsert the forgot record with a timestamp (for expiry) and the key
		sKey = StrHelper.random(32, '_0x')
		oForgot = Forgot({
			"_login": dLogin['_id'],
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
			"html_body": Templates.generate('email/forgot.html', dTpl, dLogin['locale']),
			"subject": Templates.generate('email/forgot_subject.txt', {}, dLogin['locale']),
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
		if not Login.passwordStrength(data['passwd']):
			return Services.Effect(error=1204)

		# Find the Login
		oLogin = Login.get(oForgot['_login'])
		if not oLogin:
			return Services.Effect(error=1203)

		# Store the new password and update
		oLogin['passwd'] = Login.passwordHash(data['passwd'])
		oLogin.save(changes=False)

		# Delete the forgot record
		oForgot.delete()

		# Return OK
		return Services.Effect(True)

	def search_read(self, data, sesh):
		"""Search

		Looks up logins by alias

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
		lRecords = Login.search(data['q'])

		# If we got something, fetch the records from the cache
		if not lRecords:
			lRecords = Login.cache(lRecords, raw=True)

		# Run a search and return the results
		return Services.Effect(lRecords)

	def session_read(self, data, sesh):
		"""Session

		Returns the ID of the login logged into the current session

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return Services.Effect({
			"_id": sesh['login']['_id']
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

		# Look for the login by alias
		oLogin = Login.filter({"email": data['email']}, limit=1)
		if not oLogin:
			return Services.Effect(error=1201)

		# Validate the password
		if not oLogin.passwordValidate(data['passwd']):
			return Services.Effect(error=1201)

		# Create a new session
		oSesh = Sesh.create()

		# Store the login ID and information in it
		oSesh['login'] = oLogin.record()

		# Save the session
		oSesh.save()

		# Return the session ID and primary login data
		return Services.Effect({
			"session": oSesh.id(),
			"login": {
				"_id": oSesh['login']['_id']
			}
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

	def loginEmail_update(self, data, sesh):
		"""Login Email

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

		# Find the login
		oLogin = Login.get(sesh['login']['_id'])
		if not oLogin:
			return Services.Effect(error=1104)

		# Validate the password
		if not oLogin.passwordValidate(data['email_passwd']):
			return Services.Effect(error=(1001, [('email_passwd', 'invalid')]))

		# Make sure the email is valid structurally
		if not _emailRegex.match(data['email']):
			return Services.Effect(error=(1001, [('email', 'invalid')]))

		# Look for someone else with that email
		dLogin = Login.filter({"email": data['email']}, raw=['_id'])
		if dLogin:
			return Services.Effect(error=(1206, data['email']))

		# Update the email and verified fields
		try:
			oLogin['email'] = data['email']
			oLogin['verified'] = StrHelper.random(32, '_0x')
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Update the login
		oLogin.save(changes={"creator":sesh['login']['_id']})

		# Return OK
		return Services.Effect(True)

	def loginPasswd_update(self, data, sesh):
		"""Login Password

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

		# Find the login
		oLogin = Login.get(sesh['login']['_id'])
		if not oLogin:
			return Services.Effect(error=1104)

		# Validate the password
		if not oLogin.passwordValidate(data['passwd']):
			return Services.Effect(error=(1001, [('passwd', 'invalid')]))

		# Make sure the new password is strong enough
		if not Login.passwordStrength(data['new_passwd']):
			return Services.Effect(error=1204)

		# Set the new password and save
		oLogin['passwd'] = Login.passwordHash(data['new_passwd'])
		oLogin.save(changes={"creator":sesh['login']['_id']})

		# Return OK
		return Services.Effect(True)
