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
from RestOC import Conf, DictHelper, Errors, Services, StrHelper

# Shared imports
from shared import Rights

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

	def __generateIds(self, clinician_id):
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

	def __generateToken(self, clinician_id):
		"""Generate Token

		Generates the Auth token needed for all HTTP requests

		Arguments:
			clinician_id (uint): ID of the clinician making the request

		Raises:
			EffectException

		Returns:
			str
		"""

		# Generate the encrypted IDs
		lIDs = self.__generateIds(clinician_id)

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
			raise Services.EffectException(error=(1600, oRes.text))

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
		return True

	def patient_read(self, data, sesh):
		"""Patient

		Fetches patient info

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['patient_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.CREATE,
			"ident": data['patient_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Effect(error=(1001, lErrors))

		# Generate the token
		sToken = self.__generateToken(data['clinician_id'])

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
			return Services.Effect(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Effect(error=(1602, dData['Result']['ResultDescription']))

		# Return the pharmacies
		return Services.Effect(dData['Item'])

	def patientPharmacies_read(self, data, sesh):
		"""Patient Pharmacies

		Returns the pharmacies set for the patient

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		return Services.Effect(False)

		# Verify fields
		try: DictHelper.eval(data, ['patient_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.READ,
			"ident": data['patient_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Effect(error=(1001, lErrors))

		# Generate the token
		sToken = self.__generateToken(data['clinician_id'])

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
			return Services.Effect(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Effect(error=(1602, dData['Result']['ResultDescription']))

		# Return the pharmacies
		return Services.Effect(dData['Items'])

	def patientPharmacy_create(self, data, sesh):
		"""Patient Pharmacy Create

		Adds a pharmacy to the patient's favourites

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		return Services.Effect(False)

		# Verify fields
		try: DictHelper.eval(data, ['patient_id', 'pharmacy_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.UPDATE,
			"ident": data['patient_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id', 'pharmacy_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Effect(error=(1001, lErrors))

		# Generate the token
		sToken = self.__generateToken(data['clinician_id'])

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
			return Services.Effect(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Effect(error=(1602, dData['Result']['ResultDescription']))

		# Return the pharmacies
		return Services.Effect(True)

	def patientPharmacy_delete(self, data, sesh):
		"""Patient Pharmacy Delete

		Deletes a pharmacy from the patient's favourites

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		return Services.Effect(False)

		# Verify fields
		try: DictHelper.eval(data, ['patient_id', 'pharmacy_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.UPDATE,
			"ident": data['patient_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id', 'pharmacy_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Effect(error=(1001, lErrors))

		# Generate the token
		sToken = self.__generateToken(data['clinician_id'])

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
			return Services.Effect(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Effect(error=(1602, dData['Result']['ResultDescription']))

		# Return the pharmacies
		return Services.Effect(True)

	def patientPrescriptions_read(self, data, sesh):
		"""Patient Prescriptions

		Fetches all prescriptions associated with a patient. Requires internal
		key

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['patient_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.READ,
			"ident": data['patient_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Effect(error=(1001, lErrors))

		# Generate the token
		sToken = self.__generateToken(data['clinician_id'])

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
			return Services.Effect(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Effect(error=(1602, dData['Result']['ResultDescription']))

		# If there's no items
		if not dData['Items']:
			return Services.Effect(0)

		# Go through each item and add the text versions of integer values
		for d in dData['Items']:
			d['MedicationStatusText'] = d['MedicationStatus'] in _dMedicationStatus and _dMedicationStatus[d['MedicationStatus']] or 'Unknown MedicationStatus'
			d['PharmacyName'] = d['PharmacyId'] in _dPharmacies and _dPharmacies[d['PharmacyId']] or 'Unknown Pharmacy'
			d['PrescriberName'] = d['PrescriberId'] in _dProviders and _dProviders[d['PrescriberId']] or 'Unknown Provider'
			d['StatusText'] = d['Status'] in _dStatus and _dStatus[d['Status']] or 'Unknown Status'

		# Generate and return the result
		return Services.Effect(dData['Items'])

	def patientSso_read(self, data, sesh):
		"""Patient SSO

		Fetches all a single sign on URL to DoseSpots system

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['clinician_id', 'patient_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "prescriptions",
			"right": Rights.UPDATE,
			"ident": data['patient_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Effect(error=(1001, lErrors))

		# Generate the IDs
		lIDs = self.__generateIds(data['clinician_id'])

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
		return Services.Effect(sURL)
