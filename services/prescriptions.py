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
from decimal import Decimal
from hashlib import sha512
from time import time
from urllib.parse import urlencode

# Pip imports
import arrow
import requests
from RestOC import Conf, DictHelper, Errors, Record_MySQL, Services, StrHelper

# Shared imports
from shared import Rights

# Records imports
from records.prescriptions import Medication, Pharmacy, PharmacyFill, \
									PharmacyFillError, Product

_dPharmacies = {
	6141: "Belmar Pharmacy",
	26493: "WellDyneRx",
	76881: "Pavilion Compounding",
	240931: "Anazao Health",
	56387: "WellDyneRx"
}

_dProviders = {
	43331: 'Kelley Wyant',
	43332: 'Peter Fotinos',
	43410: 'Veronica Pike',
	43411: 'Elizabeth Hernandez ',
	43423: 'Stephenie Brinson',
	43424: 'Jonathan Figg',
	43425: 'Roland Green',
	43431: 'Joseph Keenan',
	43432: 'Gary Klein',
	43433: 'Faride Ramos',
	43434: 'Ron Waldrop',
	43545: 'Josh Sawyer',
	43546: 'Dylan Whitaker',
	43547: 'Ejune Wu',
	43548: 'Chris Berry',
	43900: 'Janelle Weyer',
	44175: 'Cassandra Franco',
	44188: 'Vincent Meoli',
	44731: 'Arnaldo Trabucco',
	44756: 'Beau Butherus',
	45107: 'Edilberto Atienza',
	45135: 'Dawn Adams',
	45544: 'Gabbrielle Knabe',
	46445: 'Shannon Gruhn',
	46446: 'Cathy McCoy',
	46577: 'Tod Work',
	46709: 'Erin Lawrence',
	46710: 'Elizabeth Brown',
	46711: 'Edward Henson',
	47103: 'Harold Hibbs',
	47221: 'Fawn Munro',
	47489: 'Melissa Mendoza',
	47490: 'Dacia Mann',
	47754: 'Aaron Borengasser PA',
	47756: 'Colby Jestes',
	48200: 'Tony Underwood',
	48721: 'Heather Gall',
	48871: 'Mariama Hubbard',
	48907: 'Annissa dominguez',
	48908: 'Joe Compton',
	49258: 'Nikki Wombwell',
	49492: 'Sven Wombwell',
	50616: 'Mark Matthews ',
	50890: 'Mekala Parker',
	51575: 'Joe Compton',
	52785: 'Ben de Miranda',
	52854: 'Paige Smith',
	53780: 'Muna Orra',
	54215: 'Jamie Bittar',
	54347: 'Jessie Burgess',
	55449: 'Craig Larsen',
	56947: 'Karll Cloutier',
	57458: 'Sasha Hanson',
	58275: 'Stacy Comeau ',
	59335: 'Jessica Toath',
	62723: 'Yannick Ferreri',
	62726: 'Yannick Ferreri',
	63820: 'Maciej Malczewski',
	63821: 'Jo-Anne Stevens',
	64034: 'Payton Bernal',
	64299: 'Jeremie Lanctôt',
	64381: 'Chris Cloutier',
	65024: 'Phil Cloutier',
	65481: 'Michelle Coulombe',
	65589: 'Eddy Wilson',
	65753: 'Neifa Nayor',
	66591: 'Marc Calabrese',
	69646: 'Sam Gagnon',
	76563: 'Andrew Abraham',
	85007: 'Grace Oropesa'
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

	_install = [Medication, Pharmacy, PharmacyFill, PharmacyFillError, Product]
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

	def patient_create(self, data, sesh):
		"""Patient Create

		Creates a new patient and returns the ID

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'prescriptions', Rights.CREATE)

		# Verify fields
		try: DictHelper.eval(data, ['clinician_id', 'patient'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Convert the keys
		try:
			dData = {
				"FirstName": StrHelper.normalize(data['patient']['firstName']),
				"LastName": StrHelper.normalize(data['patient']['lastName']),
				"DateOfBirth": data['patient']['dateOfBirth'][0:10],
				"Gender": data['patient']['gender'],
				"Email": data['patient']['email'],
				"Address1": (data['patient']['address1'] or '')[0:35],
				"Address2": (data['patient']['address2'] or '')[0:35],
				"City": data['patient']['city'],
				"State": data['patient']['state'],
				"ZipCode": data['patient']['zipCode'],
				"PrimaryPhone": data['patient']['primaryPhone'],
				"PrimaryPhoneType": data['patient']['primaryPhoneType'],
				"Active": 'true'
			}
		except Exception as e:
			return Services.Response(error=(1001, str(e)))

		# Generate the token
		sToken = self._generateToken(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/webapi/api/patients' % self._host

		# Generate the headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": "Bearer %s" % sToken
		}

		# Make the request
		oRes = requests.post(sURL, data=dData, headers=dHeaders)

		print(oRes)

		# If we didn't get a 200
		if oRes.status_code != 200:
			return Services.Response(error=(1601, oRes.text))

		print(oRes.text)

		# Get the response
		dRes = oRes.json()

		print(dRes)

		# If we got an error
		if dRes['Result']['ResultCode'] == 'ERROR':
			return Services.Response(error=(1602, dData['Result']['ResultDescription']))

		# Return the ID
		return Services.Response(dRes['Id'])

	def patient_read(self, data, sesh):
		"""Patient Read

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

		# Make sure the user has the proper rights
		Rights.check(sesh, 'prescriptions', Rights.READ, data['patient_id'])

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

	def patient_update(self, data, sesh):
		"""Patient Update

		Updates patient demographic data in DoseSpot

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'prescriptions', Rights.CREATE)

		# Verify fields
		try: DictHelper.eval(data, ['clinician_id', 'patient'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure patient is a dict and has at least an id
		if not isinstance(data['patient'], dict) or 'id' not in data['patient']:
			return Services.Response(error=(1001, [('patient', 'invalid')]))

		# Convert the keys
		try:
			dData = {
				"FirstName": StrHelper.normalize(data['patient']['firstName']),
				"LastName": StrHelper.normalize(data['patient']['lastName']),
				"DateOfBirth": data['patient']['dateOfBirth'][0:10],
				"Gender": data['patient']['gender'],
				"Email": data['patient']['email'],
				"Address1": (data['patient']['address1'] or '')[0:35],
				"Address2": (data['patient']['address2'] or '')[0:35],
				"City": data['patient']['city'],
				"State": data['patient']['state'],
				"ZipCode": data['patient']['zipCode'],
				"PrimaryPhone": data['patient']['primaryPhone'],
				"PrimaryPhoneType": data['patient']['primaryPhoneType'],
				"Active": 'true'
			}
		except Exception as e:
			return Services.Response(error=(1001, str(e)))

		# Generate the token
		sToken = self._generateToken(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/webapi/api/patients/%d' % (
			self._host,
			data['patient']['id']
		)

		# Generate the headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": "Bearer %s" % sToken
		}

		# Make the request
		oRes = requests.post(sURL, data=dData, headers=dHeaders)

		# If we didn't get a 200
		if oRes.status_code != 200:
			return Services.Response(error=(1601, oRes.text))

		# Get the response
		dRes = oRes.json()

		# If we got an error
		if dRes['Result']['ResultCode'] == 'ERROR':
			return Services.Response(error=(1602, dData['Result']['ResultDescription']))

		# Return OK
		return Services.Response(True)

	def patientMedications_read(self, data, sesh):
		"""Patient Medications

		Returns the list of medication associated with the given patient

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['clinician_id', 'patient_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If it's internal
		if '_internal_' in data:

			# Verify the key, remove it if it's ok
			if not Services.internalKey(data['_internal_']):
				return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
			del data['_internal_']

		# Else
		else:

			# Make sure the user has the proper rights
			Rights.check(sesh, 'medications', Rights.READ, data['patient_id'])

		# Make sure we got ints
		lErrors = []
		for s in ['clinician_id', 'patient_id']:
			if not isinstance(data[s], int):
				lErrors.append((s, 'must be integer'))
		if lErrors: return Services.Response(error=(1001, lErrors))

		# Generate the URL
		sURL = 'https://%s/webapi/api/patients/%d/medications/history?start=1900-01-01&end=%s' % (
			self._host,
			data['patient_id'],
			arrow.get().format('YYYY-MM-DD')
		)

		# Loop for if we don't have consent
		while True:

			# Generate the headers
			dHeaders = {
				"Accept": "application/json",
				"Authorization": "Bearer %s" % self._generateToken(data['clinician_id'])
			}

			# Make the request
			oRes = requests.get(sURL, headers=dHeaders)

			# If we didn't get a 200
			if oRes.status_code != 200:
				return Services.Response(error=(1601, oRes.text))

			# Get the data
			dData = oRes.json()

			print('Medication return: %s' % dData)

			# If we got an error
			if dData['Result']['ResultCode'] == 'ERROR':

				# If it's a 1602, no consent
				if 'LogPatientMedicationHistoryConsent' in dData['Result']['ResultDescription']:

					# Generate the headers
					dHeaders = {
						"Accept": "application/json",
						"Authorization": "Bearer %s" % self._generateToken(data['clinician_id'])
					}

					# Generate the URL
					sConsentURL = 'https://%s/webapi/api/patients/%d/logMedicationHistoryConsent' % (
						self._host,
						data['patient_id']
					)

					# Make the request
					oRes = requests.post(sConsentURL, headers=dHeaders)

					# If we didn't get a 200
					if oRes.status_code != 200:
						return Services.Response(error=(1601, oRes.text))

					# Get the data
					dData = oRes.json()

					# Debugging
					print('Consent return: %s' % dData)

					# If we did not get consent
					if dData['Result']['ResultCode'] == 'ERROR':
						return Services.Response(error=(1602, dData['Result']['ResultDescription']))

					# We got consent, loop back around
					continue

				# Unknown DoseSpot error
				else:
					return Services.Response(error=(1602, dData['Result']['ResultDescription']))

			# We got a result, quit the consent loop
			break

		# If there's no items
		if not dData['Items']:
			return Services.Response([])

		# Return the medications
		return Services.Response(dData['Items'])

	def patientPharmacies_read(self, data, sesh):
		"""Patient Pharmacies

		Returns the pharmacies set for the patient

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['patient_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper rights
		Rights.check(sesh, 'prescriptions', Rights.READ, data['patient_id'])

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

		# Verify fields
		try: DictHelper.eval(data, ['patient_id', 'pharmacy_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper rights
		Rights.check(sesh, 'prescriptions', Rights.UPDATE, data['patient_id'])

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
		sURL = 'https://%s/webapi/api/patients/%d/pharmacies/%d' % (
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

		# Make sure the user has the proper rights
		Rights.check(sesh, 'prescriptions', Rights.UPDATE, data['patient_id'])

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

	def patientPrescription_create(self, data, sesh):
		"""Patient Prescription Create

		Creates a new prescription for the patient

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['patient_id', 'clinician_id', 'product_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper rights
		Rights.check(sesh, 'prescriptions', Rights.CREATE, data['patient_id'])

		# Find the product
		dProduct = Product.get(data['product_id'], raw=True)
		if not dProduct:
			return Services.Error(1104, 'product')

		# If refills missing, set to 0
		if 'refills' not in data:
			data['refills'] = 0

		# Init possible errors
		lErrors = []

		# Allow certain values to be overriden
		if 'supply' in data:
			try: dProduct['supply'] = int(data['supply'])
			except ValueError: lErrors.append(('supply', 'not an integer'))
		if 'quantity' in data:
			dProduct['quantity'] = str(data['quantity'])
		if 'directions' in data:
			dProduct['directions'] = str(data['directions'])

		# Make sure all values are ints
		for k in ['patient_id', 'clinician_id', 'refills']:
			try: data[k] = int(data[k])
			except ValueError: lErrors.append((k, 'not an integer'))

		# If there's any errors
		if lErrors:
			return Services.Error(1001, lErrors)

		# If quantity is a decimal, and it should be, convert it
		if isinstance(dProduct['quantity'], Decimal):
			dProduct['quantity'] = '{0:f}'.format(dProduct['quantity'])

		# Init the data to send to DoseSpot
		dData = {
			"DisplayName": dProduct['display'],
			"Quantity": dProduct['quantity'],
			"DaysSupply": dProduct['supply'],
			"Directions": dProduct['directions'],
			"PharmacyId": dProduct['pharmacy'],
			"DispenseUnitId": dProduct['unit_id'],
			"NoSubstitutions": True,
			"Status": 1,
			"NDC": dProduct['ndc'],
			"Refills": data['refills']
		}

		# If we have an effective date
		if 'effective' in data:
			dData['EffectiveDate'] = data['effective']

		print(dData)

		# Generate the token
		sToken = self._generateToken(data['clinician_id'])

		# Generate the URL
		sURL = 'https://%s/webapi/api/patients/%d/prescriptions/ndc' % (
			self._host,
			data['patient_id']
		)

		# Generate the headers
		dHeaders = {
			"Accept": "application/json",
			"Authorization": "Bearer %s" % sToken
		}

		# Make the request
		oRes = requests.post(sURL, headers=dHeaders, json=dData)

		# If we didn't get a 200
		if oRes.status_code != 200:
			return Services.Response(error=(1601, oRes.text))

		# Get the data
		dData = oRes.json()

		print(dData)

		# If we got an error
		if dData['Result']['ResultCode'] == 'ERROR':
			return Services.Response(error=(1602, dData['Result']['ResultDescription']))

		# Return the new prescription's ID
		return Services.Response(dData['Id'])

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

			# Make sure the user has the proper rights
			Rights.check(sesh, 'prescriptions', Rights.READ, data['patient_id'])

		# If the clinician ID isn't passed
		if 'clinician_id' not in data or not data['clinician_id']:
			data['clinician_id'] = Conf.get(('dosespot', 'clinician_id'))

		# Make sure we got ints
		lErrors = []
		for s in ['clinician_id', 'patient_id']:
			if not isinstance(data[s], int):
				lErrors.append((s, 'must be integer'))
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
		return Services.Response(dData['Items'][::-1])

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

		# Make sure the user has the proper rights
		Rights.check(sesh, 'prescriptions', Rights.UPDATE, data['patient_id'])

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

	def pharmacies_read(self, data, sesh):
		"""Pharmacies

		Returns the list of valid pharmacies to use

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Fetch and return the pharmacies
		return Services.Response(
			Pharmacy.filter({
				"active": True
			}, raw=True, orderby='name')
		)

	def pharmacyFill_create(self, data, sesh):
		"""Pharmacy Fill Create

		Create a new manual pharmacy fill

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'pharmacy_fill', Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['crm_type', 'crm_id', 'crm_order'])
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

		# Get the user name
		oResponse = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": sesh['memo_id']
		}, sesh)
		if oResponse.errorExists(): return oResponse
		dUser = oResponse.data

		# Try to create a new instance of the adhoc
		try:
			data['memo_user'] = sesh['memo_id']
			oFill = PharmacyFill(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the record and get the ID
		try:
			sID = oFill.create()
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

		# Return the ID
		return Services.Response({
			"_id": sID,
			"_created": int(time()),
			"crm_type": oFill['crm_type'],
			"crm_id": oFill['crm_id'],
			"crm_order": oFill['crm_order'],
			"customer_name": '%s %s' % (dCustomer['firstName'], dCustomer['lastName']),
			"user_name": '%s %s' % (dUser['firstName'], dUser['lastName'])
		})

	def pharmacyFillByCustomer_read(self, data, sesh):
		"""Pharmacy Fill By Customer

		Fetch all pharmacy fills and errors for a specific customer

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'prescriptions', Rights.READ)

		# Verify minimum fields
		try: DictHelper.eval(data, ['crm_type', 'crm_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find all fills associated with the customer
		lFills = PharmacyFill.filter({
			"crm_type": data['crm_type'],
			"crm_id": data['crm_id']
		}, raw=True)

		# If we got any fills
		if lFills:

			# Find all the user names
			oResponse = Services.read('monolith', 'user/name', {
				"_internal_": Services.internalKey(),
				"id": list(set([d['memo_user'] for d in lFills]))
			}, sesh)
			if oResponse.errorExists(): return oResponse
			dUsers = {k:'%s %s' % (d['firstName'], d['lastName']) for k,d in oResponse.data.items()}

			# Go through each record and add the user names
			for d in lFills:
				sUserId = str(d['memo_user'])
				d['user_name'] = sUserId in dUsers and dUsers[sUserId] or 'Unknown'

		# Find all the fill errors
		lErrors = PharmacyFillError.filter({
			"crm_type": data['crm_type'],
			"crm_id": data['crm_id'],
			"fail_count": {"neq": 0}
		}, raw=True)

		# Return the fills and errors found, if any
		return Services.Response({
			"fills": lFills,
			"errors": lErrors
		})

	def pharmacyFill_delete(self, data, sesh):
		"""Pharmacy Fill Delete

		Delete an existing pharmacy fill record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'pharmacy_fill', Rights.DELETE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the fill
		oFill = PharmacyFill.get(data['_id'])
		if not oFill:
			return Services.Response(error=1104)

		# Delete the record and return the result
		return Services.Response(
			oFill.delete()
		)

	def pharmacyFillError_create(self, data, sesh):
		"""Pharmacy Fill Error Create

		Creates a new record in the PharmacyFillError report

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Send the email
		oResponse = Services.create('communications', 'email', {
			"_internal_": Services.internalKey(),
			"text_body": str(data),
			"subject": 'pharmacyFillError_create() called',
			"to": 'bast@maleexcel.com'
		})
		if oResponse.errorExists():
			print(oResponse.error)

		# Make sure the user has the proper rights
		Rights.check(sesh, 'pharmacy_fill', Rights.CREATE)

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

		# Return the ID and customer name
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
		Rights.check(sesh, 'pharmacy_fill', Rights.DELETE)

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
		Rights.check(sesh, 'pharmacy_fill', Rights.UPDATE)

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
		Rights.check(sesh, 'pharmacy_fill', Rights.READ)

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

	def product_create(self, data, sesh):
		"""Product Create

		Creates a new product associated with a specific pharmacy

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['pharmacy'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper rights
		Rights.check(sesh, 'rx_product', Rights.CREATE, data['pharmacy'])

		# Create a new instance
		try:
			oProduct = Product(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the record and get the ID
		try:
			sID = oProduct.create(changes={"user": sesh['user_id']})
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

		# Return the ID
		return Services.Response(sID)

	def product_delete(self, data, sesh):
		"""Product Delete

		Deletes an existing product associated with a specific pharmacy

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		oProduct = Product.get(data['_id'])

		# Make sure the user has the proper rights based on the associated
		#	pharmacy
		Rights.check(sesh, 'rx_product', Rights.DELETE, oProduct['pharmacy'])

		# Delete the record and return the result
		return Services.Response(
			oProduct.delete(changes={"user": sesh['user_id']})
		)

	def product_read(self, data, sesh):
		"""Product Read

		Fetches an existing product associated with a specific pharmacy

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the record
		dProduct = Product.get(data['_id'])

		# Make sure the user has the proper rights based on the associated
		#	pharmacy
		Rights.check(sesh, 'rx_product', Rights.READ, dProduct['pharmacy'])

		# Return the product
		return Services.Response(dProduct)

	def product_update(self, data, sesh):
		"""Product Updates

		Updates an existing product associated with a specific pharmacy

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If an attempt is made to change the pharmacy
		if 'pharmacy' in data:
			return Services.Error(1603)

		# Find the record
		oProduct = Product.get(data['_id'])

		# Make sure the user has the proper rights based on the associated
		#	pharmacy
		Rights.check(sesh, 'rx_product', Rights.UPDATE, oProduct['pharmacy'])

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oProduct[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Error(1001, lErrors)

		# Update the record and return the result
		return Services.Response(
			oProduct.save(changes={"user": sesh['user_id']})
		)

	def products_read(self, data, sesh):
		"""Products Read

		Returns all products the user has access to view based on pharmacy

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Init the list of rights and the return
		dRights = {}
		lRet = []

		# If a type was passed
		dFilter = 'type' in data and {"type": data['type']} or None

		# Fetch all products
		lProducts = Product.get(filter=dFilter, raw=True, orderby='title')

		# Go through each product
		for d in lProducts:

			# If we haven't checked rights yet
			if d['pharmacy'] not in dRights:
				dRights[d['pharmacy']] = Rights.checkReturn(sesh, 'rx_product', Rights.READ, d['pharmacy'])

			# If the user can view it
			if dRights[d['pharmacy']]:
				lRet.append(d)

		# Return what's allowed
		return Services.Response(lRet)
