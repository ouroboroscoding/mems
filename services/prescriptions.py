# coding=utf8
""" Prescriptions Service

Handles all Prescriptions requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-05-10"

# Python imports
from base64 import b64encode
from hashlib import sha512
from urllib.parse import urlencode

# Pip imports
import requests
from RestOC import Conf, DictHelper, Errors, Record_MySQL, Services, StrHelper

# Shared imports
from shared import Rights

# Records imports
from records.prescriptions import Medication, Pharmacy, PharmacyFillError

_dPharmacies = {
	6141: "Belmar Pharmacy",
	26493: "WellDyneRx",
	76881: "Pavilion Compounding",
	240931: "Anazao Health",
	56387: "WellDyneRx"
}

_dProviders = {
	43432: 'Gary Klein',
	43331: 'Kelley Wyant',
	43423: 'Stephenie Brinson',
	43410: 'Veronica Pike',
	43431: 'Joseph Keenan',
	43411: 'Elizabeth Hernandez Nurse Practitioner',
	43433: 'Faride Ramos',
	43425: 'Roland Green',
	43332: 'Dr. Peter Fotinos',
	43424: 'Jonathan Figg',
	43434: 'Ron Waldrop MD',
	43900: 'Janelle Weyer',
	44188: 'Vincent Meoli',
	44731: 'Arnaldo Trabucco',
	44756: 'Beau Butherus',
	45107: 'Edilberto Atienza MD',
	45135: 'Dawn Adams',
	45544: 'Gabbrielle Knabe',
	46445: 'Shannon Gruhn',
	46446: 'Cathy McCoy',
	46577: 'Tod Work',
	46709: 'Erin Lawrence',
	46710: 'Elizabeth Brown',
	46711: 'Edward Henson',
	47103: 'Harold Hibbs',
	47221: 'Fawn  Munro',
	47754: 'Aaron Borengasser PA',
	48200: 'Tony Underwood',
	48721: 'Heather Gall - Nurse Practitioner',
	48871: 'Mariama Hubbard',
	50616: 'Mark Matthews',
	52785: 'Dr. Ben de Miranda',
	52854: 'Paige Smith',
	53780: 'Dr. Muna Orra',
	54215: 'Jamie Bittar Nurse Practitioner',
	57458: 'Sasha Hanson Nurse Practitioner',
	58275: 'Stacy Comeau Nurse Practitioner',
	59335: 'Jessica Toath Nurse Practitioner',
	65753: 'Neifa Nayor APRN',
	66591: 'Dr. Marc Calabrese',
	76563: 'Andrew Abraham M.D.'
}

_dStatus = {
	1: 'Entered',
	2: 'Printed',
	3: 'Sending',
	4: 'eRxSent',
	5: 'FaxSent',
	6: 'Error',
	7: 'Deleted',
	8: 'Requested',
	9: 'Edited',
	10: 'EpcsError',
	11: 'EpcsSigned',
	12: 'ReadyToSign'
}

_dMedicationStatus = {
	0: 'Unknown',
	1: 'Active',
	2: 'Inactive',
	3: 'Discontinued',
	4: 'Deleted',
	5: 'Completed',
	6: 'CancelRequested',
	7: 'CancelPending',
	8: 'Cancelled',
	9: 'CancelDenied',
	10: 'Changed'
}

class Prescriptions(Services.Service):
	"""Prescriptions Service class

	Service for Prescriptions access
	"""

	_install = [Medication, Pharmacy, PharmacyFillError]
	"""Record types called in install"""

	def _generateIds(self, clinician_id):
		"""Generate IDs

		Generates the encrypted clinic and clinician IDs

		Arguments:
			clinician_id (uint): ID of the clinician making the request

		Returns:
			tuple
		"""

		# Get a random key phrase
		sRand = StrHelper.random(32, ['aZ', '10'])

		# Add the clinic key to it
		sKey = '%s%s' % (sRand, self._clinic_key)

		# Encrypt it
		sEncrypt = b64encode(sha512(sKey.encode('utf-8')).digest()).decode('utf-8')

		# Cut off trailing equal signs
		if sEncrypt[-2:] == '==':
			sEncrypt = sEncrypt[0:-2]

		# Generate the clinic ID part from the random phrase and the encrypted
		#	value
		sClinicId = '%s%s' % (sRand, sEncrypt)

		# Join the clinician ID, key phrase, and clinic key
		sKey = '%d%s%s' % (clinician_id, sRand[0:22], self._clinic_key)

		# Encrypt it
		sClinicianId = b64encode(sha512(sKey.encode('utf-8')).digest()).decode('utf-8')

		# Cut off trailing equal signs
		if sClinicianId[-2:] == '==':
			sClinicianId = sClinicianId[0:-2]

		# Return the IDs
		return (sClinicId, sClinicianId)

	def _generateToken(self, clinician_id):
		"""Generate Token

		Generates the Auth token needed for all HTTP requests

		Arguments:
			clinician_id (uint): ID of the clinician making the request

		Raises:
			Services.ResponseException

		Returns:
			str
		"""

		# Generate the encrypted IDs
		lIDs = self._generateIds(clinician_id)

		# Generate the request headers
		sAuth = '%d:%s' % (self._clinic_id, lIDs[0])
		dHeaders = {
			"Authorization": 'Basic %s' % b64encode(sAuth.encode("utf-8")).decode('utf-8'),
			"Content-Type": 'application/x-www-form-urlencoded'
		}

		# Generate the form data
		dData = {
			"grant_type": 'password',
			"Username": '%d' % clinician_id,
			"Password": lIDs[1]
		}

		# Make the request for the token
		oRes = requests.post(
			'https://%s/webapi/token' % self._host,
			data=dData,
			headers=dHeaders
		)

		# If we didn't get success
		if oRes.status_code != 200:
			raise Services.ResponseException(error=(1600, oRes.text))

		# Convert the response
		dRes = oRes.json()

		# Return the token
		return dRes['access_token'];

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Store config data
		self._host = Conf.get(('dosespot', 'host'))
		self._clinic_id = Conf.get(('dosespot', 'clinic_id'))
		self._clinic_key = Conf.get(('dosespot', 'clinic_key'))
		self._clinician_id = Conf.get(('dosespot', 'clinician_id'))

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

	def patient_read(self, data, sesh):
		"""Patient

		Fetches patient info

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['patient_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.CREATE,
			"ident": data['patient_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Response(error=(1001, lErrors))

		# Generate the token
		sToken = self._generateToken(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/webapi/api/patients/%d' % (
			self._host,
			data['patient_id']
		)

		# Generate the headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": "Bearer %s" % sToken
		}

		# Make the request
		oRes = requests.get(sURL, headers=dHeaders)

		# If we didn't get a 200
		if oRes.status_code != 200:
			return Services.Response(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Response(error=(1602, dData['Result']['ResultDescription']))

		# Return the pharmacies
		return Services.Response(dData['Item'])

	def patientPharmacies_read(self, data, sesh):
		"""Patient Pharmacies

		Returns the pharmacies set for the patient

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		return Services.Response(False)

		# Verify fields
		try: DictHelper.eval(data, ['patient_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.READ,
			"ident": data['patient_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Response(error=(1001, lErrors))

		# Generate the token
		sToken = self._generateToken(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/webapi/api/patients/%d/pharmacies' % (
			self._host,
			data['patient_id']
		)

		# Generate the headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": "Bearer %s" % sToken
		}

		# Make the request
		oRes = requests.get(sURL, headers=dHeaders)

		# If we didn't get a 200
		if oRes.status_code != 200:
			return Services.Response(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Response(error=(1602, dData['Result']['ResultDescription']))

		# Return the pharmacies
		return Services.Response(dData['Items'])

	def patientPharmacy_create(self, data, sesh):
		"""Patient Pharmacy Create

		Adds a pharmacy to the patient's favourites

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		return Services.Response(False)

		# Verify fields
		try: DictHelper.eval(data, ['patient_id', 'pharmacy_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.UPDATE,
			"ident": data['patient_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id', 'pharmacy_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Response(error=(1001, lErrors))

		# Generate the token
		sToken = self._generateToken(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/webapi/api/patients/%d/pharmacies/%s' % (
			self._host,
			data['patient_id'],
			data['pharmacy_id']
		)

		# Generate the headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": "Bearer %s" % sToken
		}

		# Make the request
		oRes = requests.post(sURL, headers=dHeaders)

		# If we didn't get a 200
		if oRes.status_code != 200:
			return Services.Response(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Response(error=(1602, dData['Result']['ResultDescription']))

		# Return the pharmacies
		return Services.Response(True)

	def patientPharmacy_delete(self, data, sesh):
		"""Patient Pharmacy Delete

		Deletes a pharmacy from the patient's favourites

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		return Services.Response(False)

		# Verify fields
		try: DictHelper.eval(data, ['patient_id', 'pharmacy_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.UPDATE,
			"ident": data['patient_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id', 'pharmacy_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Response(error=(1001, lErrors))

		# Generate the token
		sToken = self._generateToken(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/webapi/api/patients/%d/pharmacies/%s' % (
			self._host,
			data['patient_id'],
			data['pharmacy_id']
		)

		# Generate the headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": "Bearer %s" % sToken
		}

		# Make the request
		oRes = requests.delete(sURL, headers=dHeaders)

		# If we didn't get a 200
		if oRes.status_code != 200:
			return Services.Response(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Response(error=(1602, dData['Result']['ResultDescription']))

		# Return the pharmacies
		return Services.Response(True)

	def patientPrescriptions_read(self, data, sesh=None):
		"""Patient Prescriptions

		Fetches all prescriptions associated with a patient. Requires internal
		key

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If we have no session and no key
		if not sesh and '_internal_' not in data:
			return Services.Response(error=(1001, [('_internal_', 'missing')]))

		# Verify fields
		try: DictHelper.eval(data, ['patient_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If it's internal
		if '_internal_' in data:

			# Verify the key, remove it if it's ok
			if not Services.internalKey(data['_internal_']):
				return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
			del data['_internal_']

		# Else
		else:

			# Make sure the user has the proper permission to do this
			oResponse = Services.read('auth', 'rights/verify', {
				"name": "prescriptions",
				"right": Rights.READ,
				"ident": data['patient_id']
			}, sesh)
			if not oResponse.data:
				return Services.Response(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Response(error=(1001, lErrors))

		# Generate the token
		sToken = self._generateToken(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/webapi/api/patients/%d/prescriptions' % (
			self._host,
			data['patient_id']
		)

		# Generate the headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": "Bearer %s" % sToken
		}

		# Make the request
		oRes = requests.get(sURL, headers=dHeaders)

		# If we didn't get a 200
		if oRes.status_code != 200:
			return Services.Response(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Response(error=(1602, dData['Result']['ResultDescription']))

		# If there's no items
		if not dData['Items']:
			return Services.Response([])

		# Go through each item and add the text versions of integer values
		for d in dData['Items']:
			d['MedicationStatusText'] = d['MedicationStatus'] in _dMedicationStatus and _dMedicationStatus[d['MedicationStatus']] or 'Unknown MedicationStatus'
			d['PharmacyName'] = d['PharmacyId'] in _dPharmacies and _dPharmacies[d['PharmacyId']] or 'Unknown Pharmacy'
			d['PrescriberName'] = d['PrescriberId'] in _dProviders and _dProviders[d['PrescriberId']] or 'Unknown Provider'
			d['StatusText'] = d['Status'] in _dStatus and _dStatus[d['Status']] or 'Unknown Status'

		# Generate and return the result
		return Services.Response(dData['Items'])

	def patientSso_read(self, data, sesh):
		"""Patient SSO

		Fetches all a single sign on URL to DoseSpots system

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['clinician_id', 'patient_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.UPDATE,
			"ident": data['patient_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Response(error=(1001, lErrors))

		# Generate the IDs
		lIDs = self._generateIds(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/LoginSingleSignOn.aspx?%s' % (
			self._host,
			urlencode({
				"SingleSignOnClinicId": self._clinic_id,
				"SingleSignOnUserId": '%d' % data['clinician_id'],
				"SingleSignOnPhraseLength": '32',
				"SingleSignOnCode": lIDs[0],
				"SingleSignOnUserIdVerify": lIDs[1],
				"PatientId": '%d' % data['patient_id']
			})
		)

		# Return the URL
		return Services.Response(sURL)

	def pharmacyFillError_create(self, data, sesh):
		"""Pharmacy Fill Error Create

		Creates a new record in the PharmacyFillError report

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "pharmacy_fill",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['crm_type', 'crm_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If the CRM is Konnektive
		if data['crm_type'] == 'knk':

			# Check the customer exists
			oResponse = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": data['crm_id']
			}, sesh)
			if oResponse.errorExists(): return oResponse
			dCustomer = oResponse.data

		# Else, invalid CRM
		else:
			return Services.Response(error=1003)

		# If type is still being sent
		if 'type' in data:
			del data['type']

		# Try to create a new instance of the adhoc
		try:
			oFillError = PharmacyFillError(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the record and get the ID
		try:
			sID = oFillError.create()
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

		# Create the record and return the result
		return Services.Response({
			"_id": sID,
			"customer_name": '%s %s' % (dCustomer['firstName'], dCustomer['lastName'])
		})

	def pharmacyFillError_delete(self, data, sesh):
		"""Pharmacy Fill Error Delete

		Deletes an existing record from the PharmacyFillError report

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "pharmacy_fill",
			"right": Rights.DELETE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oPharmacyFillError = PharmacyFillError.get(data['_id'])
		if not oPharmacyFillError:
			return Services.Response(error=1104)

		# Delete the record and return the result
		return Services.Response(
			oPharmacyFillError.delete()
		)

	def pharmacyFillError_update(self, data, sesh):
		"""Pharmacy Fill Error Update

		Updates the ready or orderId values of an existing pharmacyFillError record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "pharmacy_fill",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If we have neither the ready or the order ID
		if 'ready' not in data and 'crm_order' not in data:
			return Services.Response(error=(1001, [('ready', 'missing'), ('crm_order', 'missing')]))

		# Find the record
		oPharmacyFillError = PharmacyFillError.get(data['_id'])
		if not oPharmacyFillError:
			return Services.Response(error=1104)

		# Update the ready state if we got it
		if 'ready' in data:
			oPharmacyFillError['ready'] = data['ready'] and True or False

		# Update the order ID if we got it
		if 'crm_order' in data:
			oPharmacyFillError['crm_order'] = data['crm_order']

		# Save and return the result
		return Services.Response(
			oPharmacyFillError.save()
		)

	def pharmacyFillErrors_read(self, data, sesh):
		"""Pharmacy Fill Errors

		Returns all pharmacy fill error records with a count of at least one

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "pharmacy_fill",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Init the base requirements
		dFilter = {"fail_count": {
			"neq": 0
		}}

		# If a type or ID were passed
		if 'crm_type' in data:
			dFilter['crm_type'] = data['crm_type']
		if 'crm_id' in data:
			dFilter['crm_id'] = data['crm_id']

		# Fetch all the records joined with the trigger table
		lRecords = PharmacyFillError.filter(dFilter, raw=True, orderby=[('fail_count', 'DESC')])

		# If we have records
		if lRecords:

			# Find all the customer names
			oResponse = Services.read('monolith', 'customer/name', {
				"_internal_": Services.internalKey(),
				"customerId": [d['crm_id'] for d in lRecords]
			}, sesh)
			if oResponse.errorExists(): return oResponse
			dCustomers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oResponse.data.items()}

			# Go through each record and add the customer and user names
			for d in lRecords:
				d['customer_name'] = d['crm_id'] in dCustomers and dCustomers[d['crm_id']] or 'Unknown'

			# Return all records
			return Services.Response(lRecords)

		# Else return an empty array
		else:
			return Services.Response([])
