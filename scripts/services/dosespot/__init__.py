# coding=utf8
""" Dosespot Service

Handles all Dosespot requests
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
import urllib.parse

# Pip imports
import requests
from RestOC import Conf, DictHelper, Errors, Services, Sesh, StrHelper

_dPharmacies = {
	6141: "Belmar Pharmacy",
	26493: "CastiaRx",
	76881: "Pavilion Compounding",
	240931: "Anazao Health",
	56387: "WellDyne"
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
	66591: 'Dr. Marc Calabrese'
}

class Dosespot(Services.Service):
	"""Dosespot Service class

	Service for Dosespot CRM access

	Extends: shared.Services.Service
	"""

	def __generateToken(self, clinician_id):
		"""Generate Token

		Generates the Auth token needed for all HTTP requests

		Arguments:
			clinician_id {uint} -- ID of the clinician making the request

		Raises:
			EffectException

		Returns:
			str
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
		sUserId = b64encode(sha512(sKey.encode('utf-8')).digest()).decode('utf-8')

		# Cut off trailing equal signs
		if sUserId[-2:] == '==':
			sUserId = sUserId[0:-2]
			print('User ID: %s' % sUserId)

		# Generate the request headers
		sAuth = '%d:%s' % (self._clinic_id, sClinicId)
		dHeaders = {
			"Authorization": 'Basic %s' % b64encode(sAuth.encode("utf-8")).decode('utf-8'),
			"Content-Type": 'application/x-www-form-urlencoded'
		}

		# Generate the form data
		dData = {
			"grant_type": 'password',
			"Username": '%d' % clinician_id,
			"Password": sUserId
		}

		# Make the request for the token
		oRes = requests.post(
			'https://%s/token' % self._host,
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

	def patientPrescriptions_read(self, data):
		"""Patient Prescriptions

		Fetches all prescriptions associated with a patient. Requires internal
		key

		Arguments:
			data {dict} -- Data sent with the request

		Returns:
			Services.Effect
		"""

		# Verify fields
		try: DictHelper.eval(data, ['clinician_id', 'patient_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, "missing") for f in e.args]))

		# Make sure we got ints
		for s in ['clinician_id', 'patient_id']:
			lErrors = []
			if not isinstance(data[s], int): lErrors.append((s, 'must be integer'))
			if lErrors: return Services.Effect(error=(1001, lErrors))

		# Generate the token
		sToken = self.__generateToken(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/api/patients/%d/prescriptions' % (
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

		# Go through each item and update the pharmacy and provider
		for d in dData['Items']:
			d['PharmacyName'] = d['PharmacyId'] in _dPharmacies and _dPharmacies[d['PharmacyId']] or 'Unknown Pharmacy'
			d['PrescriberName'] = d['PrescriberId'] in _dProviders and _dProviders[d['PrescriberId']] or 'Unknown Provider'

		# Generate and return the result
		return Services.Effect(dData['Items'])
