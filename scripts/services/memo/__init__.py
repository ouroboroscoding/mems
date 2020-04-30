# coding=utf8
""" Memo Service

Handles all Memo requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-04-26"

# Python imports
import re
from time import time

# Pip imports
import bcrypt
from redis import StrictRedis
from RestOC import Conf, DictHelper, Errors, Services, \
					Sesh, StrHelper, Templates

# Service imports
from .records import CustomerClaimed, CustomerCommunication, CustomerMsgPhone, \
						Forgot, User

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

class Memo(Services.Service):
	"""Memo Service class

	Service for Memoorization, sign in, sign up, etc.

	Extends: shared.Services.Service
	"""

	_install = [Forgot]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Memo
		"""

		# Create a connection to Redis
		self._redis = StrictRedis(**Conf.get(('redis', 'primary'), {
			"host": "localhost",
			"port": 6379,
			"db": 0
		}))

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

	def msgsClaimed_read(self, data, sesh):
		"""Messages: Claimed

		Fetches the list of phone numbers and name associated that the
		user has claimed

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""

		# Fetch and return the data
		return Services.Effect(
			CustomerMsgPhone.claimed(sesh['user_id'])
		)

	def msgsUnclaimed_read(self, data, sesh):
		"""Messages: Unclaimed

		Fetches all summaries with incoming messages that have not been hidden
		or already claimed by a rep

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""

		# Fetch and return the data
		return Services.Effect(
			CustomerMsgPhone.unclaimed()
		)

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
		dUser = User.filter({"email": data['email']}, raw=['id'], limit=1)
		if not dUser:
			return Services.Effect(False)

		# Look for a forgot record by user id
		oForgot = Forgot.get(dUser['id'])

		# Is there already a key in the user?
		if oForgot and 'regenerate' not in data:

			# Is it not expired?
			if oForgot['expires'] > int(time()):
				return Services.Effect(True)

		# Upsert the forgot record with a timestamp (for expiry) and the key
		sKey = StrHelper.random(32, '_0x')
		oForgot = Forgot({
			"user": dUser['id'],
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
		oUser = User.get(oForgot['user'])
		if not oUser:
			return Services.Effect(error=1203)

		# Store the new password and update
		oUser['passwd'] = User.passwordHash(data['passwd'])
		oUser.save(changes=False)

		# Delete the forgot record
		oForgot.delete()

		# Return OK
		return Services.Effect(True)

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
			"user" : {
				"id": sesh['user_id']
			}
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
		try: DictHelper.eval(data, ['userName', 'passwd'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the user by alias
		oUser = User.filter({"userName": data['userName']}, limit=1)
		if not oUser:
			return Services.Effect(error=1201)

		# Validate the password
		if not bcrypt.checkpw(data['passwd'].encode('utf8'), oUser['password'].encode('utf8')):
			return Services.Effect(error=1201)

		# Create a new session
		oSesh = Sesh.create()

		# Store the user ID and information in it
		oSesh['user_id'] = oUser['id']

		# Save the session
		oSesh.save()

		# Return the session ID and primary user data
		return Services.Effect({
			"session": oSesh.id(),
			"user": {
				"id": oSesh['user_id']
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

	def user_read(self, data, sesh):
		"""User Read

		Fetches the logged in user and returns their data

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the user

		Returns:
			Effect
		"""

		# Fetch it from the DB
		dUser = User.get(sesh['user_id'], raw=True)

		print(dUser)

		# If it doesn't exist
		if not dUser:
			return Services.Effect(error=1104)

		# Remove the passwd
		del dUser['password']

		# Return the user data
		return Services.Effect(dUser)

	def user_update(self, data, sesh):
		"""User Update

		Updates the logged in user

		Arguments:
			data {dict} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the user

		Returns:
			Effect
		"""

		# Fetch it from the cache
		oUser = User.get(sesh['user_id'])

		# Remove fields that can't be changed
		del data['id']
		if 'password' in data: del data['passwd']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oUser[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Effect(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Effect(
			oUser.save(changes={"user": sesh['user_id']})
		)

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
		oUser = User.get(sesh['user']['id'])
		if not oUser:
			return Services.Effect(error=1104)

		# Validate the password
		if not bcrypt.checkpw(data['passwd'].encode('utf8'), oUser['password'].encode('utf8')):
			return Services.Effect(error=(1001, [('passwd', 'invalid')]))

		# Make sure the new password is strong enough
		if not User.passwordStrength(data['new_passwd']):
			return Services.Effect(error=1204)

		# Set the new password and save
		oUser['passwd'] = bcrypt.hashpw(data['new_passwd'], bcrypt.gensalt())
		oUser.save(changes={"user":sesh['user']['id']})

		# Return OK
		return Services.Effect(True)
