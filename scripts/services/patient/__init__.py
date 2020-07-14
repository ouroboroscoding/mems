# coding=utf8
""" Patient Service

Handles all Patient (person associated with customer) requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-06-26"

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
from .records import Account, AccountSetup, Forgot

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

class Patient(Services.Service):
	"""Patient Service class

	Service for Patientorization, sign in, sign up, etc.
	"""

	_install = [Account, AccountSetup, Forgot]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Patient
		"""

		# Create a connection to Redis
		self._redis = StrictRedis(**Conf.get(('redis', 'primary'), {
			"host": "localhost",
			"port": 6379,
			"db": 0
		}))

		# Pass the Redis connection to records that need it
		Account.redis(self._redis)

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

	def accountForgot_create(self, data):
		"""Account Password Forgot (Generate)

		Creates the key that will be used to allow a patient to change their
		password if they forgot it

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'url'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the account by email
		dAccount = Account.filter({"email": data['email']}, raw=['_id', 'locale'], limit=1)
		if not dAccount:
			return Services.Effect(False)

		# Look for a forgot record by account id
		oForgot = Forgot.get(dAccount['_id'])

		# Is there already a key for the account?
		if oForgot and 'regenerate' not in data:

			# Is it not expired?
			if oForgot['expires'] > int(time()):
				return Services.Effect(True)

		# Upsert the forgot record with a timestamp (for expiry) and the key
		sKey = StrHelper.random(32, '_0x')
		oForgot = Forgot({
			"_account": dAccount['_id'],
			"expires": int(time()) + Conf.get(("services", "patient", "forgot_expire"), 600),
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

		# Email the patient the key
		oEffect = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/patient/forgot.html', dTpl, dAccount['locale']),
			"subject": Templates.generate('email/patient/forgot_subject.txt', {}, dAccount['locale']),
			"to": data['email'],
		})
		if oEffect.errorExists():
			return oEffect

		# Return OK
		return Services.Effect(True)

	def accountForgot_update(self, data):
		"""Account Password Forgot (Change Password)

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
		if not Account.passwordStrength(data['passwd']):
			return Services.Effect(error=1204)

		# Find the Account
		oAccount = Account.get(oForgot['_account'])
		if not oAccount:
			return Services.Effect(error=1203)

		# Store the new password and update
		oAccount['passwd'] = Account.passwordHash(data['passwd'])
		oAccount.save(changes=False)

		# Delete the forgot record
		oForgot.delete()

		# Return OK
		return Services.Effect(True)

	def session_read(self, data, sesh):
		"""Session

		Returns the ID of the patient logged into the current session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return Services.Effect({
			"account" : {
				"_id": sesh['user_id']
			}
		})

	def signin_create(self, data):
		"""Signin

		Signs a patient into the system

		Arguments:
			data (dict): The data passed to the request

		Returns:
			Result
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'passwd'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the patient by email address
		oAccount = Account.filter({"email": data['email']}, limit=1)
		if not oAccount:
			return Services.Effect(error=1201)

		# Validate the password
		if not oAccount.passwordValidate(data['passwd']):
			return Services.Effect(error=1201)

		# Create a new session
		oSesh = Sesh.create()

		# Store the account ID and information in it
		oSesh['user_id'] = oAccount['_id']

		# Save the session
		oSesh.save()

		# Return the session ID and primary account data
		return Services.Effect({
			"session": oSesh.id(),
			"account": {
				"_id": oSesh['user_id']
			}
		})

	def signout_create(self, data, sesh):
		"""Signout

		Called to sign out a patient and destroy their session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the account

		Returns:
			Services.Effect
		"""

		# Close the session so it can no longer be found/used
		sesh.close()

		# Return OK
		return Services.Effect(True)

	def setupStart_create(self, data, sesh):
		"""Setup Start

		Creates a record used in starting the process to create a customer
		patient login account, then sends out an email to the customer to
		get them to verify themselves

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "patient_account",
			"right": Rights.CREATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['email'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Check if we already have an account with that email
		if Account.exists(data['email'], 'email') or \
			AccountSetup.exists(data['email'], 'email'):
			return Services.Effect(error=1900)

		# Add the ID and attempts to the data
		data['_id'] = StrHelper.random(32, ['aZ', '10', '!*'])
		data['attempts'] = 0

		# Create an instance of the setup record
		try:
			oSetup = AccountSetup(data)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record
		if not oSetup.create():
			return Services.Effect(error=1100)

		# Patient setup email template variables
		dTpl = {
			"key": oSetup['_id'],
			"url": data['url'] + oSetup['_id']
		}

		# Email the patient the key
		oEffect = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/patient/setup.html', dTpl, 'en-US'),
			"subject": Templates.generate('email/patient/setup_subject.txt', {}, 'en-US'),
			"to": data['email'],
		})
		if oEffect.errorExists():
			return oEffect

		# Return OK
		return Services.Effect(True)

	def setupValidate_create(self, data):
		"""Setup Update

		Checks the passed key against the setup table to make sure the patient
		is who they say they are,

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['key', 'dob', 'lname', 'passwd'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Look for the record
		oSetup = AccountSetup.get(data['key'])
		if not oSetup:
			return Services.Effect(error=1905)

		# Check if we already have an account with that email
		if Account.exists(data['email'], 'email'):
			return Services.Effect(error=1900)

		# Check the dob and last name matches
		if data['dob'] != oSetup['dob'] or \
			data['lname'].lower() != oSetup['lname'].lower():

			# Increment the attempts
			oSetup['attempts'] += 1

			# If we've hit the limit, delete the record and return
			if oSetup['attempts'] == Conf.get(('services', 'patient', 'attempts')):
				oSetup.delete()
				return Services.Effect(error=1906)

			# Else, save and return
			else:
				oSetup.save()
				return Services.Effect(error=1001)

		# Validate the password strength
		if not Account.passwordStrength(data['passwd']):
			return Services.Effect(error=1904)

		# Create an instance of the account
		try:
			oAccount = Account({
				"email": oSetup['email'],
				"passwd": data['passwd'],
				"locale": 'locale' in data and data['locale'] or 'en-US',
				"crm_type": oSetup['crm_type'],
				"crm_id": oSetup['crm_id'],
				"rx_type": oSetup['rx_type'],
				"rx_id": oSetup['rx_id']
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record
		if not oAccount.create():
			return Services.Effect(error=1100)

		# Delete the setup
		oSetup.delete()

		# Return OK
		return Services.Effect(True)
