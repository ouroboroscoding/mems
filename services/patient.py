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

# Records imports
from records.patient import Account, AccountSetup, Verify

# Support request types
_dSupportRequest = {
	"cancel_order": "%(crm_type)s Patient %(crm_id)s would like to cancel their order.",
	"payment": "%(crm_type)s Patient %(crm_id)s would like to change their payment information.",
	"urgent_address": "%(crm_type)s Patient %(crm_id)s changed shipping address and needs an urgent update to the pharmacy"
}

# Regex for validating email
_emailRegex = re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

class Patient(Services.Service):
	"""Patient Service class

	Service for Patientorization, sign in, sign up, etc.
	"""

	_install = [Account, AccountSetup, Verify]
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

		# Return self for chaining
		return self

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

	def account_read(self, data, sesh):
		"""Account

		Returns the account data associated with the signed in user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# If there's an ID, check permissions
		if '_id' in data:

			# Make sure the user has the proper permission to do this
			oEff = self.rightsVerify_read({
				"name": "patient",
				"right": Rights.READ
			}, sesh)
			if not oEff.data:
				return Services.Effect(error=Rights.INVALID)

		# Else, assume the signed in user's Record
		else:
			data['_id'] = sesh['user_id']

		# Fetch it from the cache
		dAccount = Account.get(data['_id'], raw=True)

		# If it doesn't exist
		if not dAccount:
			return Services.Effect(error=1104)

		# Remove the passwd
		del dAccount['passwd']

		# Return the user data
		return Services.Effect(dAccount)

	def accountEmail_update(self, data, sesh):
		"""Account Email Update

		Changes the accounts email address

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'url'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# If there's an ID, check permissions
		if '_id' in data:

			# Make sure the user has the proper permission to do this
			oEff = self.rightsVerify_read({
				"name": "patient",
				"right": Rights.UPDATE
			}, sesh)
			if not oEff.data:
				return Services.Effect(error=Rights.INVALID)

		# Else, assume the signed in user's Record
		else:
			data['_id'] = sesh['user_id']

		# Convert the email to lowercase
		data['email'] = data['email'].lower()

		# Check if we already have an account with that email
		if Account.exists(data['email'], 'email') or \
			AccountSetup.exists(data['email'], 'email'):
			return Services.Effect(error=1900)

		# Find the account
		oAccount = Account.get(data['_id'])
		if not oAccount:
			return Services.Effect(error=1104)

		# Update the email
		oAccount['email'] = data['email']
		oAccount['verified'] = False

		# If they're KNK
		if oAccount['crm_type'] == 'knk':

			# Find the customer in Konnektive
			oEff = Services.read('konnektive', 'customer', {
				"customerId": oAccount['crm_id']
			}, sesh)
			if oEff.errorExists():
				return oEff

			# Store the first name
			sFirst = oEff.data['shipping']['firstName']

		# Upsert the record with the
		sKey = StrHelper.random(32, '_0x')
		oVerify = Verify({
			"_account": oAccount['_id'],
			"key": sKey
		})
		if not oVerify.create(conflict="replace"):
			return Services.Effect(error=1100)

		# Forgot email template variables
		dTpl = {
			"first": sFirst,
			"url": "%s%s" % (
				data['url'],
				sKey
			)
		}

		# Email the patient the key
		oEff = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/patient/verify.html', dTpl, oAccount['locale']),
			"subject": Templates.generate('email/patient/verify_subject.txt', {}, oAccount['locale']),
			"to": data['email']
		})
		if oEff.errorExists():
			return oEff

		# Save and return the result
		return Services.Effect(
			oAccount.save(changes={"user": sesh['user_id']})
		)

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
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Convert the email to lowercase
		data['email'] = data['email'].lower()

		# Look for the account by email
		dAccount = Account.filter({"email": data['email']}, raw=['_id', 'locale', 'crm_type', 'crm_id'], limit=1)
		if not dAccount:
			return Services.Effect(False)

		# Look for a verify record by account id
		oVerify = Verify.get(dAccount['_id'])

		# Is there already a key for the account?
		if oVerify and 'regenerate' not in data:
			return Services.Effect(True)

		# If they're KNK
		if dAccount['crm_type'] == 'knk':

			# Create a session for the user associated with the account
			oSesh = Sesh.create()
			oSesh['user_id'] = dAccount['_id']
			oSesh.save()

			# Find the customer in Konnektive
			oEff = Services.read('konnektive', 'customer', {
				"customerId": dAccount['crm_id']
			}, oSesh)
			oSesh.close()
			if oEff.errorExists():
				return Services.Effect(error=(oEff.error['code'], 'crm'))

			# Store the first name
			sFirst = oEff.data['shipping']['firstName']

		# Upsert the forgot record with a timestamp (for expiry) and the key
		sKey = StrHelper.random(32, '_0x')
		oVerify = Verify({
			"_account": dAccount['_id'],
			"key": sKey
		})
		if not oVerify.create(conflict="replace"):
			return Services.Effect(error=1100)

		# Forgot email template variables
		dTpl = {
			"first": sFirst,
			"url": "%s%s" % (
				data['url'],
				sKey
			)
		}

		# Email the patient the key
		oEff = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/patient/forgot.html', dTpl, dAccount['locale']),
			"subject": Templates.generate('email/patient/forgot_subject.txt', {}, dAccount['locale']),
			"to": data['email']
		})
		if oEff.errorExists():
			return oEff

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
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the verify by the key
		oVerify = Verify.filter({"key": data['key']}, limit=1)
		if not oVerify:
			return Services.Effect(error=1903) # Don't let people know if the key exists or not

		# Make sure the new password is strong enough
		if not Account.passwordStrength(data['passwd']):
			return Services.Effect(error=1904)

		# Find the Account
		oAccount = Account.get(oVerify['_account'])
		if not oAccount:
			return Services.Effect(error=1903)

		# Store the new password and update
		oAccount['passwd'] = Account.passwordHash(data['passwd'])
		oAccount.save(changes=False)

		# Delete the verify record
		oVerify.delete()

		# Return OK
		return Services.Effect(True)

	def accountVerify_update(self, data):
		"""Account Veverify

		Validates the email via key and marks the acccount as verified

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['key'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the verify by the key
		oVerify = Verify.filter({"key": data['key']}, limit=1)
		if not oVerify:
			return Services.Effect(error=1903) # Don't let people know if the key exists or not

		# Find the Account
		oAccount = Account.get(oVerify['_account'])
		if not oAccount:
			return Services.Effect(error=1903)

		# Update the verified flag
		oAccount['verified'] = True
		oAccount.save(changes=False)

		# Delete the verify record
		oVerify.delete()

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
		try: DictHelper.eval(data, ['dob', 'crm_type', 'crm_id', 'rx_type', 'rx_id', 'url'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Init setup
		dSetup = {
			"_id": StrHelper.random(32, ['aZ', '10', '!*']),
			"attempts": 0,
			"dob": data['dob'],
			"user": sesh['user_id']
		}

		# If they're KNK
		if data['crm_type'] == 'knk':

			# Find the customer in Konnektive
			oEff = Services.read('konnektive', 'customer', {
				"customerId": data['crm_id']
			}, sesh)
			if oEff.errorExists():
				return Services.Effect(error=(oEff.error['code'], 'crm'))

			dSetup['crm_type'] = 'knk'
			dSetup['crm_id'] = str(data['crm_id'])
			dSetup['email'] = oEff.data['email'].lower()
			dSetup['lname'] = oEff.data['shipping']['lastName']
			sFirst = oEff.data['shipping']['firstName']

		# Else, invalid CRM type
		else:
			return Services.Effect(error=(1001, [('crm_type', 'invalid')]))

		# Check if we already have an account with that email
		if Account.exists(dSetup['email'], 'email') or \
			AccountSetup.exists(dSetup['email'], 'email'):
			return Services.Effect(error=1900)

		# If they're DoseSpot
		if data['rx_type'] == 'ds':

			# Find the patient in DoseSpot
			oEff = Services.read('prescriptions', 'patient/prescriptions', {
				"patient_id": int(data['rx_id'])
			}, sesh)
			if oEff.errorExists():
				return Services.Effect(error=(oEff.error['code'], 'rx'))

			dSetup['rx_type'] = 'ds'
			dSetup['rx_id'] = str(data['rx_id'])

		# Else, invalid RX type
		else:
			return Services.Effect(error=(1001, [('rx_type', 'invalid')]))

		# Create an instance of the setup record
		try:
			oSetup = AccountSetup(dSetup)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record
		if not oSetup.create():
			return Services.Effect(error=1100)

		# Patient setup email template variables
		dTpl = {
			"first": sFirst,
			"url": data['url'] + oSetup['_id']
		}

		# Email the patient the key
		oEff = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/patient/setup.html', dTpl, 'en-US'),
			"subject": Templates.generate('email/patient/setup_subject.txt', {}, 'en-US'),
			"to": dSetup['email']
		})
		if oEff.errorExists():
			return oEff

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
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the record
		oSetup = AccountSetup.get(data['key'])
		if not oSetup:
			return Services.Effect(error=1905)

		# Check if we already have an account with that email
		if Account.exists(oSetup['email'], 'email'):
			return Services.Effect(error=1900)

		# Check the dob and last name matches
		if data['dob'] != oSetup['dob'] or \
			data['lname'].lower() != oSetup['lname'].lower():

			# Increment the attempts
			oSetup['attempts'] += 1

			# If we've hit the limit, delete the record and return
			if oSetup['attempts'] == Conf.get(('services', 'patient', 'max_attempts')):
				oSetup.delete()
				return Services.Effect(error=1906)

			# Else, save and return
			else:
				oSetup.save()
				return Services.Effect(error=1907)

		# Validate the password strength
		if not Account.passwordStrength(data['passwd']):
			return Services.Effect(error=1904)

		# Hash the password
		data['passwd'] = Account.passwordHash(data['passwd'])

		# Create an instance of the account
		try:
			oAccount = Account({
				"email": oSetup['email'],
				"passwd": data['passwd'],
				"verified": True,
				"locale": 'locale' in data and data['locale'] or 'en-US',
				"crm_type": oSetup['crm_type'],
				"crm_id": oSetup['crm_id'],
				"rx_type": oSetup['rx_type'],
				"rx_id": oSetup['rx_id']
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the record
		if not oAccount.create(changes={"user": oSetup['user']}):
			return Services.Effect(error=1100)

		# Create the permissions
		sWarning = None
		oSesh = Sesh.create()
		oSesh['user_id'] = oSetup['user']
		oSesh.save()
		oEff = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": oAccount['_id'],
			"permissions": {
				"customers": {"rights": 3, "idents": oAccount['crm_id']},
				"prescriptions": {"rights": 1, "idents": oAccount['rx_id']}
			}
		}, oSesh)
		oSesh.close()
		if oEff.errorExists():
			print(oEff)
			sWarning = 'Failed to create permissions for agent'

		# Delete the setup
		oSetup.delete()

		# Return OK
		return Services.Effect(True, warning=sWarning)

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
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Convert the email to lowercase
		data['email'] = data['email'].lower()

		# Look for the patient by email address
		oAccount = Account.filter({"email": data['email']}, limit=1)
		if not oAccount:
			return Services.Effect(error=1901)

		# Validate the password
		if not oAccount.passwordValidate(data['passwd']):
			return Services.Effect(error=1901)

		# If the email hasn't been verified
		if not oAccount['verified']:
			return Services.Effect(error=1908)

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

	def supportRequest_create(self, data, sesh):
		"""Support Request

		A patient is requesting support contact them

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the account

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['type'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# If the type is invalid
		if data['type'] not in _dSupportRequest:
			return Services.Effect(error=(1001, [('type', 'invalid') for f in e.args]))

		# Find the signed in user
		oAccount = Account.get(sesh['user_id'], raw=['crm_type', 'crm_id'])
		if not oAccount:
			return Services.Effect(error=1104)

		# Email content
		sBody = _dSupportRequest[data['type']] % {
			"crm_type": "Konnektive",
			"crm_id": oAccount['crm_id']
		}

		# Email the patient the key
		oEff = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"text_body": sBody,
			"subject": 'Patient Portal Support Request',
			"to": Conf.get(('services', 'patient', 'support_email'))
		})
		if oEff.errorExists():
			return oEff

		# Return OK
		return Services.Effect(True)
