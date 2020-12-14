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
import arrow
from redis import StrictRedis
from RestOC import Conf, DictHelper, Errors, Services, \
					Sesh, StrHelper, Templates

# Shared imports
from shared import Environment, Rights

# Records imports
from records.patient import Account, AccountSetup, AccountSetupAttempt, \
							Activity, Verify

# Service imports
from . import emailError

# Support request types
_dSupportRequest = {
	"cancel_order": "to cancel their order",
	"payment": "to change their payment info",
	"urgent_address": "an urgent change to their shipping address (address already changed in the CRM)"
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

		# Get config
		self._conf = Conf.get(('services', 'patient'), {
			"max_attempts": 3,
			"override": "admin@maleexcel.com",
			"support_email": "admin@maleexcel.com"
		})

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
		"""Account Read

		Returns the account data associated with the signed in user

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If there's an ID, check permissions
		if '_id' in data:

			# Make sure the user has the proper permission to do this
			oResponse = Services.read('auth', 'rights/verify', {
				"name": "patient_account",
				"right": Rights.READ
			}, sesh)
			if not oResponse.data:
				return Services.Response(error=Rights.INVALID)

		# Else, assume the signed in user's Record
		else:
			data['_id'] = sesh['user_id']

		# Fetch it from the cache
		dAccount = Account.get(data['_id'], raw=True)

		# If it doesn't exist
		if not dAccount:
			return Services.Response(error=1104)

		# Remove the passwd
		del dAccount['passwd']

		# Return the user data
		return Services.Response(dAccount)

	def accountByCRM_read(self, data, sesh):
		"""Account By CRM

		Returns the ID of the patient account by looking it up from their CRM
		details

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "patient_account",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['crm_type', 'crm_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# The filter used to find the record
		dFilter = {
			"crm_type": data['crm_type'],
			"crm_id": str(data['crm_id'])
		}

		# Returned fields
		lFields = ['_id', 'email', 'dob', 'lname', 'crm_type', 'crm_id', 'rx_type', 'rx_id', 'attempts']

		# Try to find the record in the setup table
		dAccount = AccountSetup.filter(dFilter, raw=lFields, limit=1)

		# If there's no such setup account
		if not dAccount:

			# Try to find the record in the account table
			lFields.remove('attempts')
			lFields.remove('dob')
			lFields.remove('lname')
			dAccount = Account.filter(dFilter, raw=lFields, limit=1)

			# If there's no such account
			if not dAccount:
				return Services.Response(False)

			# Add attempts and activate state
			dAccount['attempts'] = None
			dAccount['activated'] = True
			dAccount['dob'] = None
			dAccount['lname'] = None

		# Else, we found setup
		else:
			dAccount['activated'] = False

		# Return the ID
		return Services.Response(dAccount)

	def accountEmail_update(self, data, sesh):
		"""Account Email Update

		Changes the accounts email address

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'url'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If there's an ID, check permissions
		if '_id' in data:

			# Make sure the user has the proper permission to do this
			oResponse = Services.read('auth', 'rights/verify', {
				"name": "patient_account",
				"right": Rights.UPDATE
			}, sesh)
			if not oResponse.data:
				return Services.Response(error=Rights.INVALID)

		# Else, assume the signed in user's Record
		else:
			data['_id'] = sesh['user_id']

		# Convert the email to lowercase
		data['email'] = data['email'].lower()

		# Check if we already have an account with that email
		if Account.exists(data['email'], 'email') or \
			AccountSetup.exists(data['email'], 'email'):
			return Services.Response(error=1900)

		# Find the account
		oAccount = Account.get(data['_id'])
		if not oAccount:
			return Services.Response(error=1104)

		# Update the email
		oAccount['email'] = data['email']
		oAccount['verified'] = False

		# If they're KNK
		if oAccount['crm_type'] == 'knk':

			# Find the customer in Konnektive
			oResponse = Services.read('konnektive', 'customer', {
				"customerId": oAccount['crm_id']
			}, sesh)
			if oResponse.errorExists():
				return oResponse

			# Store the first name
			sFirst = oResponse.data['shipping']['firstName']

		# Upsert the record with the
		sKey = StrHelper.random(32, '_0x')
		oVerify = Verify({
			"_account": oAccount['_id'],
			"key": sKey
		})
		if not oVerify.create(conflict="replace"):
			return Services.Response(error=1100)

		# Forgot email template variables
		dTpl = {
			"first": sFirst,
			"url": "%s%s" % (
				data['url'],
				sKey
			)
		}

		# Email the patient the key
		oResponse = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/patient/verify.html', dTpl, oAccount['locale']),
			"subject": Templates.generate('email/patient/verify_subject.txt', {}, oAccount['locale']),
			"to": self._conf['override'] or data['email']
		})
		if oResponse.errorExists():
			return oResponse

		# Save and return the result
		return Services.Response(
			oAccount.save(changes={"user": sesh['user_id']})
		)

	def accountForgot_create(self, data):
		"""Account Password Forgot (Generate)

		Creates the key that will be used to allow a patient to change their
		password if they forgot it

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'url'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Convert the email to lowercase
		data['email'] = data['email'].lower()

		# Look for the account by email
		dAccount = Account.filter({"email": data['email']}, raw=['_id', 'locale', 'crm_type', 'crm_id'], limit=1)
		if not dAccount:
			return Services.Response(False)

		# Look for a verify record by account id
		oVerify = Verify.get(dAccount['_id'])

		# Is there already a key for the account?
		if oVerify and 'regenerate' not in data:
			return Services.Response(True)

		# If they're KNK
		if dAccount['crm_type'] == 'knk':

			# Create a session for the user associated with the account
			oSesh = Sesh.create()
			oSesh['user_id'] = dAccount['_id']
			oSesh.save()

			# Find the customer in Konnektive
			oResponse = Services.read('konnektive', 'customer', {
				"customerId": dAccount['crm_id']
			}, oSesh)
			oSesh.close()
			if oResponse.errorExists():
				return Services.Response(error=(oResponse.error['code'], 'crm'))

			# Store the first name
			sFirst = oResponse.data['shipping']['firstName']

		# Upsert the forgot record with a timestamp (for expiry) and the key
		sKey = StrHelper.random(32, '_0x')
		oVerify = Verify({
			"_account": dAccount['_id'],
			"key": sKey
		})
		if not oVerify.create(conflict="replace"):
			return Services.Response(error=1100)

		# Forgot email template variables
		dTpl = {
			"first": sFirst,
			"url": "%s%s" % (
				data['url'],
				sKey
			)
		}

		# Email the patient the key
		oResponse = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/patient/forgot.html', dTpl, dAccount['locale']),
			"subject": Templates.generate('email/patient/forgot_subject.txt', {}, dAccount['locale']),
			"to": self._conf['override'] or data['email']
		})
		if oResponse.errorExists():
			return oResponse

		# Return OK
		return Services.Response(True)

	def accountForgot_update(self, data):
		"""Account Password Forgot (Change Password)

		Validates the key and changes the password to the given value

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['passwd', 'key'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the verify by the key
		oVerify = Verify.filter({"key": data['key']}, limit=1)
		if not oVerify:
			return Services.Response(error=1903) # Don't let people know if the key exists or not

		# Make sure the new password is strong enough
		if not Account.passwordStrength(data['passwd']):
			return Services.Response(error=1904)

		# Find the Account
		oAccount = Account.get(oVerify['_account'])
		if not oAccount:
			return Services.Response(error=1903)

		# Store the new password and update
		oAccount['passwd'] = Account.passwordHash(data['passwd'])
		oAccount.save(changes=False)

		# Delete the verify record
		oVerify.delete()

		# Return OK
		return Services.Response(True)

	def accountRx_update(self, data, sesh):
		"""Account RX Update

		Allows setting of RX type/ID after account creation

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id', 'rx_type', 'rx_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "patient_account",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Assume no real account
		bAccount = False

		# Try to find the record in the setup table
		oAccount = AccountSetup.get(data['_id'])

		# If there's no such setup account
		if not oAccount:

			# Try to find the record in the account table
			oAccount = Account.get(data['_id'])

			# If there's no such account
			if not oAccount:
				return Services.Response(error=1104)

			# We have a completed account
			bAccount = True

		# If the patient already has an RX ID
		if oAccount['rx_id'] is not None:
			return Services.Response(error=1909)

		# If they're DoseSpot
		if data['rx_type'] == 'ds':

			# Find the patient in DoseSpot
			oResponse = Services.read('prescriptions', 'patient/prescriptions', {
				"patient_id": int(data['rx_id'])
			}, sesh)
			if oResponse.errorExists():
				return Services.Response(error=(oResponse.error['code'], 'rx'))

			# Store the RX values
			oAccount['rx_type'] = 'ds'
			oAccount['rx_id'] = str(data['rx_id'])

		# Else, invalid RX type
		else:
			return Services.Response(error=(1001, [('rx_type', 'invalid')]))

		# Append the new permission
		if bAccount:
			oResponse = Services.update('auth', 'permissions', {
				"_internal_": Services.internalKey(),
				"append": True,
				"user": oAccount['_id'],
				"permissions": {
					"prescriptions": {"rights": 1, "idents": oAccount['rx_id']}
				}
			}, sesh)
			if oResponse.errorExists(): return oResponse

		# Save the record and return the result
		return Services.Response(
			oAccount.save(changes={"user": sesh['user_id']})
		)

	def accountVerify_update(self, data):
		"""Account Veverify

		Validates the email via key and marks the acccount as verified

		Arguments:
			data (dict): Data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['key'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the verify by the key
		oVerify = Verify.filter({"key": data['key']}, limit=1)
		if not oVerify:
			return Services.Response(error=1903) # Don't let people know if the key exists or not

		# Find the Account
		oAccount = Account.get(oVerify['_account'])
		if not oAccount:
			return Services.Response(error=1903)

		# Update the verified flag
		oAccount['verified'] = True
		oAccount.save(changes=False)

		# Delete the verify record
		oVerify.delete()

		# Return OK
		return Services.Response(True)

	def session_read(self, data, sesh):
		"""Session

		Returns the ID of the patient logged into the current session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return Services.Response({
			"account" : {
				"_id": sesh['user_id']
			}
		})

	def setupAttempts_read(self, data, sesh):
		"""Setup Attempts

		Returns the list of failed setup attempts on a specific key

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "patient_account",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['key'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Fetch and return any records found
		return Services.Response(
			AccountSetupAttempt.filter(
				{"_setup": data['key']},
				raw=['_created', 'dob', 'lname'],
				orderby=[['_created', 'DESC']]
			)
		)

	def setupReset_update(self, data, sesh):
		"""Setup Reset

		Resets the attempt count on the setup account so the patient can
		try again

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "patient_account",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['key'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the account
		oSetup = AccountSetup.get(data['key'])
		if not oSetup:
			return Services.Response(error=1104)

		# Reset the count
		oSetup['attempts'] = 0

		# Save and return the result
		return Services.Response(
			oSetup.save()
		)

	def setupStart_create(self, data, sesh):
		"""Setup Start

		Creates a record used in starting the process to create a customer
		patient login account, then sends out an email to the customer to
		get them to verify themselves

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "patient_account",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify fields
		try: DictHelper.eval(data, ['dob', 'crm_type', 'crm_id', 'url'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Init setup
		dSetup = {
			"attempts": 0,
			"dob": data['dob'],
			"user": sesh['user_id']
		}

		# If they're KNK
		if data['crm_type'] == 'knk':

			# Find the customer in Konnektive
			oResponse = Services.read('konnektive', 'customer', {
				"customerId": data['crm_id']
			}, sesh)
			if oResponse.errorExists():
				return Services.Response(error=(oResponse.error['code'], 'crm'))

			dSetup['crm_type'] = 'knk'
			dSetup['crm_id'] = str(data['crm_id'])
			dSetup['email'] = oResponse.data['email'].lower()
			dSetup['lname'] = oResponse.data['shipping']['lastName']
			sFirst = oResponse.data['shipping']['firstName']

		# Else, invalid CRM type
		else:
			return Services.Response(error=(1001, [('crm_type', 'invalid')]))

		# Check if we already have an account with that email
		if Account.exists(dSetup['email'], 'email') or \
			AccountSetup.exists(dSetup['email'], 'email'):
			return Services.Response(error=1900)

		# If we have an rx type
		if 'rx_type' in data:

			# If we have no ID
			if 'rx_id' not in data:
				return Services.Response(error=(1001, [('rx_id', 'missing')]))

			# If they're DoseSpot
			if data['rx_type'] == 'ds':

				# Find the patient in DoseSpot
				oResponse = Services.read('prescriptions', 'patient/prescriptions', {
					"patient_id": int(data['rx_id'])
				}, sesh)
				if oResponse.errorExists():
					return Services.Response(error=(oResponse.error['code'], 'rx'))

				dSetup['rx_type'] = 'ds'
				dSetup['rx_id'] = str(data['rx_id'])

			# Else, invalid RX type
			else:
				return Services.Response(error=(1001, [('rx_type', 'invalid')]))

		# Create an instance of the setup record
		try:
			oSetup = AccountSetup(dSetup)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the record
		if not oSetup.create():
			return Services.Response(error=1100)

		# Patient setup email template variables
		dTpl = {
			"first": sFirst,
			"url": data['url'] + oSetup['_id']
		}

		# Email the patient the key
		oResponse = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"html_body": Templates.generate('email/patient/setup.html', dTpl, 'en-US'),
			"subject": Templates.generate('email/patient/setup_subject.txt', {}, 'en-US'),
			"to": self._conf['override'] or dSetup['email']
		})
		if oResponse.errorExists():
			return oResponse

		# Return the ID of the account
		return Services.Response(oSetup['_id'])

	def setupUpdate_update(self, data, sesh):
		"""Account Setup Update

		Updates the setup data in an existing record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "patient_account",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Try to find the record in the account setup table
		oSetup = AccountSetup.get(data['_id'])
		if not oSetup:
			return Services.Response(error=1104)

		# Remove fields that can't be changed
		for k in ['_id', '_created', 'crm_type', 'crm_id', 'user']:
			if k in data: del data[k]

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oSetup[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Response(
			oSetup.save()
		)

	def setupValidate_create(self, data):
		"""Setup Update

		Checks the passed key against the setup table to make sure the patient
		is who they say they are,

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['key', 'dob', 'lname', 'passwd'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the record
		oSetup = AccountSetup.get(data['key'])
		if not oSetup:

			# Check for a patient account
			oAccount = Account.get(data['key'])
			if oAccount:
				return Services.Response(error=1911)

			# No patient account, the key just doesn't exist
			return Services.Response(error=1905)

		# If the attempts has hit the limit
		if oSetup['attempts'] >= self._conf['max_attempts']:
			return Services.Response(error=1906)

		# Check if we already have an account with that email
		if Account.exists(oSetup['email'], 'email'):
			return Services.Response(error=1900)

		# Check the dob and last name matches
		if data['dob'] != oSetup['dob'] or \
			data['lname'].lower() != oSetup['lname'].lower():

			# Store the attempt
			try:
				oAttempt = AccountSetupAttempt({
					"_setup": data['key'],
					"dob": str(data['dob']),
					"lname": str(data['lname'])
				})
				oAttempt.create()

			# If it fails for any reason, email the developer and just move on
			except Exception as e:
				emailError('Patient Setup Validation Failed', 'Sent: %s\n\n DB: %s\n\nException: %s' % (
					str(data),
					str(oSetup.record()),
					str(e)
				))

			# Increment the attempts and save
			oSetup['attempts'] += 1
			oSetup.save()

			# If we've hit the limit return an error limit error
			if oSetup['attempts'] == self._conf['max_attempts']:
				return Services.Response(error=1906)

			# Else return failure error
			return Services.Response(error=1907)

		# Validate the password strength
		if not Account.passwordStrength(data['passwd']):
			return Services.Response(error=1904)

		# Hash the password
		data['passwd'] = Account.passwordHash(data['passwd'])

		# Create an instance of the account using the same ID used for the setup
		try:
			oAccount = Account({
				"_id": oSetup['_id'],
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
			return Services.Response(error=(1001, e.args[0]))

		# Create the record
		if not oAccount.create(changes={"user": oSetup['user']}):
			return Services.Response(error=1100)

		# Init permissions
		dPerms = {
			"customers": {"rights": 3, "idents": oAccount['crm_id']}
		}

		# If there's an RX
		if oSetup['rx_type'] and oSetup['rx_id']:
			dPerms['prescriptions'] = {"rights": 1, "idents": oAccount['rx_id']}

		# Create the permissions
		sWarning = None
		oSesh = Sesh.create()
		oSesh['user_id'] = oSetup['user']
		oSesh.save()
		oResponse = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": oAccount['_id'],
			"permissions": dPerms
		}, oSesh)
		oSesh.close()
		if oResponse.errorExists():
			print(oResponse)
			sWarning = 'Failed to create permissions for patient'

		# Delete the setup
		oSetup.delete()

		# Return OK
		return Services.Response(True, warning=sWarning)

	def signin_create(self, data, environ):
		"""Signin

		Signs a patient into the system

		Arguments:
			data (dict): The data passed to the request
			environ (dict): Info related to the request

		Returns:
			Result
		"""

		# Verify fields
		try: DictHelper.eval(data, ['email', 'passwd'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Convert the email to lowercase
		data['email'] = data['email'].lower()

		# Look for the patient by email address
		oAccount = Account.filter({"email": data['email']}, limit=1)
		if not oAccount:
			return Services.Response(error=1901)

		# Validate the password
		if not oAccount.passwordValidate(data['passwd']):
			return Services.Response(error=1901)

		# If the email hasn't been verified
		if not oAccount['verified']:
			return Services.Response(error=1908)

		# Create a new session
		oSesh = Sesh.create()

		# Store the account ID and information in it
		oSesh['user_id'] = oAccount['_id']

		# Save the session
		oSesh.save()

		# Get the current date/time
		oDT = arrow.get()

		# Log the activity
		try:
			dActivity = {
				"account": oAccount['_id'],
				"date": oDT.format('YYYY-MM-DD'),
				"time": oDT.format('HH:mm:ss'),
				"type": 'signin',
				"ip": Environment.getClientIP(environ)
			}
			oActivity = Activity(dActivity)
			oActivity.create()
		except Exception as e:
			emailError('Activity Log Failed', '%s\n\n%s' % (
				str(e),
				str(dActivity)
			))

		# Return the session ID and primary account data
		return Services.Response({
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
			Services.Response
		"""

		# Close the session so it can no longer be found/used
		sesh.close()

		# Return OK
		return Services.Response(True)

	def supportRequest_create(self, data, sesh):
		"""Support Request

		A patient is requesting support contact them

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the account

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['type'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If the type is invalid
		if data['type'] not in _dSupportRequest:
			return Services.Response(error=(1001, [('type', 'invalid') for f in e.args]))

		# Find the signed in user
		oAccount = Account.get(sesh['user_id'], raw=['crm_type', 'crm_id'])
		if not oAccount:
			return Services.Response(error=1104)

		# Get the phone number of the customer
		if oAccount['crm_type'] == 'knk':

			# Contact Konnektive
			oResponse = Services.read('konnektive', 'customer', {
				"customerId": oAccount['crm_id']
			}, sesh)
			if oResponse.errorExists(): return oResponse

			# Store the phone number
			sNumber = oResponse.data['phone']

		else:
			emailError('Support Request Failed', 'Invalid CRM Type\n\n%s' % (
				str(oAccount)
			))

		# Add the request as an incoming SMS
		oResponse = Services.create('monolith', 'message/incoming', {
			"_internal_": Services.internalKey(),
			"customerPhone": sNumber,
			"recvPhone": "0000000000",
			"content": "PP: Customer has requested %s" % _dSupportRequest[data['type']]
		})
		if oResponse.errorExists():
			emailError('Support Request Failed', 'Failed to add SMS\n\n%s\n\n%s\n\n%s' % (
				str(data),
				str(oAccount),
				str(oResponse)
			))

		# Return OK
		return Services.Response(True)
