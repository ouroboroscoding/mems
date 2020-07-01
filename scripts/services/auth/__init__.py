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

# Shared imports
from shared import Rights

# Service imports
from .records import Forgot, Permission, User, UserPatient, UserPatientSetup

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

class Auth(Services.Service):
	"""Auth Service class

	Service for Authorization, sign in, sign up, etc.
	"""

	_install = [Forgot, Permission, User, UserPatient, UserPatientSetup]
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

		# Return OK
		return True

	def patientVerify_create(self, data, sesh):
		"""Patient Verify Create

		Creates a record used in starting the process to create a customer
		patient login account, then sends out an email to the customer to
		start the process of verifying themselves

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = self.verify_read({
			"name": "patient_user",
			"right": Rights.CREATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['type', "crm_id"])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Which CRM is this customer from?
		if data['type'] == 'knk':

			# Fetch the customer's details from Konnektive
			oEff = Services.read('konnektive', 'customer', {
				"id": data['crm_id']
			})
			if oEff.errorExists():
				return oEff

			# Store the email address
			sEmail = oEff.data['email']

		# Create an instance of the setup record
		try:
			oSetup = UserPatientSetup({
				"_id": StrHelper.random(32, ['aZ', '10', '!*']),
				"type": data['type'],
				"crm_id": data['crm_id']
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record
		if not oSetup.create():
			return Services.Effect(error=1100)

		# Patient setup email template variables
		dTpl = {
			"key": oSetup['_id'],
			"url": Conf.get(('services', 'auth', 'pp_verify_link')) % oSetup['_id']
		}

		# Email the user the key
		oEffect = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/patient_setup.html', dTpl, dUser['locale']),
			"subject": Templates.generate('email/patient_setup_subject.txt', {}, dUser['locale']),
			"to": sEmail,
		})
		if oEffect.errorExists():
			return oEffect

		# Return OK
		return Services.Effect(True)

	def permissions_read(self, data, sesh):
		"""Permissions

		Returns all permissions associated with a user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

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
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper rights
		oEff = self.verify_read({
			"name": "permission",
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

		# Validate and store the new permissions
		lRecords = []
		for sName,iRights in data['permissions'].items():
			lErrors = []
			try:
				lRecords.append(Permission({
					"user": data['user'],
					"name": sName,
					"rights": iRights
				}))
			except ValueError as e:
				lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Effect(error=(1001, lErrors))

		# Delete all the existing permissions if there are any
		if dOldPermissions:
			Permission.deleteGet(data['user'], 'user')

		# Create the new permissions if there are any
		if lRecords:
			Permission.createMany(lRecords)

		# Get and store the changes
		dChanges = {"user": sesh['user_id']}
		if dOldPermissions and data['permissions']:
			dChanges['permissions'] = User.generateChanges(dOldPermissions, data['permissions'])
		elif data['permissions']:
			dChanges['permissions'] = {"old": None, "new": "inserted"}
		else:
			dChanges['permissions'] = {"old": dOldPermissions, "new": None}
		User.addChanges(data['user'], dChanges)

		# Clear the user from the cache
		User.cacheClear(data['user'])

		# Return OK
		return Services.Effect(True)

	def search_read(self, data, sesh):
		"""Search

		Looks up users by alias

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['filter'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# If the filter isn't a dict
		if not isinstance(data['filter'], dict):
			return Services.Effect(error=(1001, [('filter', "must be a key:value store")]))

		# If fields is not a list
		if 'fields' in data and not isinstance(data['fields'], list):
			return Services.Effect(error=(1001, [('fields', "must be an list")]))

		# Search based on the data passed
		lRecords = [d['_id'] for d in User.filter(data['filter'], raw=['_id'])]

		# If we got something, fetch the records from the cache
		if lRecords:
			lRecords = User.cache(lRecords, raw=('fields' in data and data['fields'] or True))

		# Remove the passwd
		for d in lRecords:
			del d['passwd']

		# Run a search and return the results
		return Services.Effect(lRecords)

	def session_read(self, data, sesh):
		"""Session

		Returns the ID of the user logged into the current session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

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
			data (dict): The data passed to the request

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
			"user": {
				"id": oSesh['user_id']
			}
		})

	def signout_create(self, data, sesh):
		"""Signout

		Called to sign out a user and destroy their session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

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
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

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

		# Add defaults
		if 'locale' not in data: data['locale'] = 'en-US'
		if 'country' not in data: data['country'] = 'US'

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
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

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

		# Remove the passwd
		del dUser['passwd']

		# Return the user data
		return Services.Effect(dUser)

	def user_update(self, data, sesh):
		"""User Update

		Updates an existing user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Effect
		"""

		# If there's an ID, check permissions
		if '_id' in data or data['_id'] != sesh['user_id']:

			# If the ID isn't set
			if not data['_id']:
				return Services.Effect(error=(1001, [('_id', 'missing')]))

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
		if 'email' in data: del data['email']
		if 'passwd' in data: del data['passwd']

		# If passed, store permissions for later
		mPermissions = 'permissions' in data and data.pop('permissions') or None

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oUser[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Effect(error=(1001, lErrors))

		# Update the record
		bRes = oUser.save(changes={"user": sesh['user_id']})

		# If it was updated, clear the cache
		if bRes:
			User.cacheClear(oUser['_id'])

		# Return the result
		return Services.Effect(bRes)

	def userEmail_update(self, data, sesh):
		"""User Email

		Changes the email for the current signed in user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

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
			return Services.Effect(error=1200)

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
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

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

	def userPasswdForgot_create(self, data):
		"""User Password Forgot (Generate)

		Creates the key that will be used to allow a user to change their
		password if they forgot it

		Arguments:
			data (dict): Data sent with the request

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

	def userPasswdForgot_update(self, data):
		"""User Password Forgot (Change Password)

		Validates the key and changes the password to the given value

		Arguments:
			data (dict): Data sent with the request

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


	def verify_read(self, data, sesh):
		"""Verify

		Checks the user currently in the session has access to the requested
		permission

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

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
