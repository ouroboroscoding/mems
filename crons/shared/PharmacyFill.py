# coding=utf8
"""Pharmacy Fill

Shared functionality for looking up orders and generating data needed to fill
them with a pharmacy
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-02"

# Pip imports
import arrow
from RestOC import DictHelper, Services

# Service includes
from services.konnektive import Konnektive
from records.monolith import DsPatient
from records.prescriptions import Expiring, Medication, Pharmacy

# Module variables
_mdMedById = {}
_mdMedByName = {}
_mdPharmacies = {}
_moKonnektive = Konnektive()
_moYearAgo = None
_mo335Ago = None
"""Variables used by the module"""

# Cron imports
from crons import emailError

def initialise():
	"""Initialise

	Initialises the modules by fetching any needed information

	Returns:
		None
	"""

	global _mdMedById, _mdMedByName, _mdPharmacies, _moKonnektive, _moYearAgo, _mo335Ago

	# Fetch all the valid pharmacies and store them by id => name
	_mdPharmacies = {
		d['pharmacyId']:d['name']
		for d in Pharmacy.get(raw=['name', 'pharmacyId'])
	}

	# Fetch all the medications and store them by id and name
	lMeds = Medication.get(raw=['name', 'dsIds', 'synonyms'])
	for d in lMeds:
		_mdMedByName[d['name']] = d['synonyms'].split(',')
		for s in d['dsIds'].split(','):
			_mdMedById[int(s)] = d['name']

	# Initialise service instances
	_moKonnektive.initialise()

	# Get 365 & 335 days ago
	_moYearAgo = arrow.get().shift(years=-1)
	_mo335Ago = arrow.get().shift(days=-335)

def medication(descr):
	"""Medication

	Attempts to find a medication based on the description given

	Arguments:
		descr (str): The description of the product in the order

	Returns:
		str
	"""

	# Go through each medication we have
	for k,v in _mdMedByName.items():

		# Go through each synonym we have for it
		for s in v:

			# If the synonym exists in the description
			if s in descr.lower():

				# Return the medication name
				return k

	# We found nothing, return false
	return 'unknown'

def prescriptions(l, max_date=None):
	"""Prescriptions

	Takes the list of prescriptions and returns a distinct list of the latest RX
	by medication

	Arguments:
		l (dict[]): A list of prescriptions associated with the customer
		max_date (arrow): Optional, reject prescriptions newer than this date

	Returns:
		dict[]
	"""

	# Keep track of meds
	dRet = {};

	# Go through each prescription found
	for d in l:

		# If we have a max date
		if max_date and max_date < arrow.get(d['WrittenDate']):
			print('SKIPPING PRESCRIPTION')
			continue

		# If it's an error, requested, or deleted, skip it
		if d['Status'] in [6,7,8]:
			continue

		# If the ID is 0, find the product by description
		if d['LexiGenProductId'] == 0:
			sMed = medication(d['DisplayName'])

		# Else, use the ID to find the product in our list
		else:
			sMed = d['LexiGenProductId'] in _mdMedById and \
					_mdMedById[d['LexiGenProductId']] or \
					'unknown'

		# Look for the pharmacy
		sPharmacy = d['PharmacyId'] in _mdPharmacies and \
						_mdPharmacies[d['PharmacyId']] or \
						'unknown'

		# If the product hasn't been seen yet
		if sMed not in dRet:
			dRet[sMed] = {
				"id": d['PrescriptionId'],
				"pharmacy": sPharmacy,
				"date": d['WrittenDate'],
				"display": '%s (%s)' %(d['DisplayName'], d['Quantity']),
				"effective": d['EffectiveDate'] and d['EffectiveDate'] or d['WrittenDate'],
				"refills": int(d['Refills'])
			}

		# Else, overwrite it if the date is newer
		elif dRet[sMed]['date'] < d['WrittenDate']:
			dRet[sMed] = {
				"id": d['PrescriptionId'],
				"pharmacy": sPharmacy,
				"date": d['WrittenDate'],
				"display": '%s (%s)' %(d['DisplayName'], d['Quantity']),
				"effective": d['EffectiveDate'] and d['EffectiveDate'] or d['WrittenDate'],
				"refills": int(d['Refills'])
			}

	# Return the data found
	return dRet

def process(item, backfill=None):
	"""Process

	Takes an item and figures out where it goes or returns an error if there
	is one. On success returns {"status": True, "data": dict[]}, data being
	everything necessary to flll the order. On failure returns {"status": False,
	"data": str}, data being the error message

	Arguments:
		item (dict): All data necessary to find the medication and rx
		backfill (dict): A dict of order and max_date, used specifically
							for transfer from old system to new
		trigger (str): The ID of a trigger if we want to update the existing
						instead of making a new one

	Returns:
		dict
	"""

	# Import global vars
	global _moYearAgo, _mo335Ago

	# Init the possible return data
	dRet = {
		"crm_type": item['crm_type'],
		"crm_id": item['crm_id']
	}

	# First, find the order
	if item['crm_type'] == 'knk':

		# If we need to backfill an older trigger
		if backfill:

			# Store the order ID
			dRet['crm_order'] = backfill['order']['orderId']

			# Store the order
			dOrder = backfill['order']

			# Turn the date into an object, and overwrite the 1 year date
			backfill['max_date'] = arrow.get(backfill['max_date'])
			_moYearAgo = backfill['max_date'].shift(years=-1)

		# Else
		else:

			# Store the order ID
			dRet['crm_order'] = item['crm_order']

			# Look it up by crm_order
			lOrders = _moKonnektive._request('order/query', {
				"orderId": item['crm_order']
			})

			# If there's no order
			if not lOrders:
				return {"status": False, "data": "ORDER NOT FOUND"}

			# Store the order
			dOrder = lOrders[0];

		# Turn the order items into a list
		lItems = [];
		if 'items' in dOrder and dOrder['items']:
			lItems = [{
				"canceled": d['purchaseStatus'] == 'CANCELLED',
				"name": d['name'],
				"purchaseId": d['purchaseId']
			} for d in dOrder['items'].values()]

		# Store the relevant data
		dRet['rx'] = ''
		dRet['type'] = dOrder['orderType'] == 'NEW_SALE' and 'initial' or 'refill'
		dRet['email'] = dOrder['emailAddress']
		dRet['phone'] = dOrder['phoneNumber']
		dRet['first'] = dOrder['shipFirstName']
		dRet['last'] = dOrder['shipLastName']
		dRet['address1'] = dOrder['shipAddress1']
		dRet['address2'] = dOrder['shipAddress2']
		dRet['city'] = dOrder['shipCity']
		dRet['state'] = dOrder['shipState']
		dRet['country'] = dOrder['shipCountry']
		dRet['postalCode'] = dOrder['shipPostalCode']

	# Else, invalid CRM type
	else:
		return {"status": False, "data": "INVALID CRM TYPE"}

	# If we have no items
	if not lItems:
		return {"status": False, "data": "NO ITEMS IN ORDER"};

	# Fetch the DoseSpot patientId
	dDsPatient = DsPatient.filter({
		"customerId": str(item['crm_id'])
	}, raw=['patientId', 'dateOfBirth'], limit=1);

	# If there's no DoseSpot patient record
	if not dDsPatient or not dDsPatient['patientId']:
		return {"status": False, "data": "NOT IN DOSESPOT"}

	# Set DOB field
	dRet['dob'] = dDsPatient['dateOfBirth'];

	# Fetch the patient's prescriptions from dosespot
	oResponse = Services.read('prescriptions', 'patient/prescriptions', {
		"_internal_": Services.internalKey(),
		"patient_id": int(dDsPatient['patientId'])
	})
	if oResponse.errorExists():
		return {"status": False, "data": str(oResponse.error)}

	# If we didn't get data back anything from DoseSpot
	if not oResponse.data:
		return {"status": False, "data": "NO PRESCRIPTIONS IN DOSESPOT"}

	# Store full list of prescriptions
	lPrescriptions = oResponse.data

	# Filter down the prescriptions by medication
	dPrescriptions = prescriptions(lPrescriptions, (backfill and backfill['max_date'] or None))

	# If we have no prescriptions
	if not dPrescriptions:
		return {"status": False, "data": "NO VALID PRESCRIPTIONS"}

	# If we found an unknown product
	if 'unknown' in dPrescriptions:
		emailError('Unknown Product', '\n'.join([str({
			"LexiGenProductId": d['LexiGenProductId'],
			"GenericProductName": d['GenericProductName'],
			"DisplayName": d['DisplayName']
		}) for d in lPrescriptions]))

	# If we found an unknown pharmacy
	if next((d for d in dPrescriptions.values() if d['pharmacy'] == 'unknown'), None):
		emailError('Unknown Pharmacy', str({
			"crm_type": item['crm_type'],
			"crm_id": item['crm_id'],
			"PharmacyIds": ','.join([str(d['PharmacyId']) for d in lPrescriptions])
		}))

	# If we have only one prescription and one product
	if len(dPrescriptions.values()) == 1 and len(lItems) == 1:

		# Get the only key in the prescriptions
		sMedication = list(dPrescriptions.keys())[0]
		dPrescription = dPrescriptions[sMedication]

		# If the pharmacy is not known
		if dPrescription['pharmacy'] == 'unknown':
			return {"status": False, "data": "UNKNOWN PHARMACY"}

		# Check the date for expiration
		oEffective = arrow.get(dPrescription['effective'])
		if oEffective < _moYearAgo:
			return {"status": False, "data": "EXPIRED PRESCRIPTION"}

		# Check for expiring soon
		if oEffective < _mo335Ago:
			oExpiring = Expiring({
				"crm_type": item['crm_type'],
				"crm_id": item['crm_id'],
				"crm_order": item['crm_order'],
				"crm_purchase": lItems[0]['purchaseId'],
				"rx_id": str(dPrescription['id']),
				"step": 0
			})
			oExpiring.create(conflict='replace')

		# Set the product and add the row to the pharmacy
		dRet['medication'] = dPrescription['display']
		dRet['pharmacy'] = dPrescription['pharmacy']
		dRet['ds_id'] = dPrescription['id']

		# Return success
		return {"status": True, "data": [dRet]}

	# Else we have multiple products or prescriptions
	else:

		# Init the list
		lRet = []

		# Go through each product in the order
		for m in lItems:

			# Try to find the medication
			sMedication = medication(m['name'])

			# If it's unknown
			if sMedication == 'unknown':
				emailError('Unknown Product', m['name'])
				return {"status": False, "data": "UNKNOWN PRODUCT (%s)" % m['name']}

			# If we don't have a matching prescription
			if sMedication not in dPrescriptions:
				return {"status": False, "data": "NO MATCHING PRESCRIPTION (%s)" % sMedication};

			# Store the prescription
			dPrescription = dPrescriptions[sMedication]

			# If the pharmacy is not known
			if dPrescription['pharmacy'] == 'unknown':
				return {"status": False, "data": "UNKNOWN PHARMACY"}

			# Check the date for expiration
			oEffective = arrow.get(dPrescription['effective'])
			if oEffective < _moYearAgo:
				return {"status": False, "data": "EXPIRED PRESCRIPTION"}

			# Check for expiring soon
			if oEffective < _mo335Ago:
				oExpiring = Expiring({
					"crm_type": item['crm_type'],
					"crm_id": item['crm_id'],
					"crm_order": item['crm_order'],
					"crm_purchase": m['purchaseId'],
					"rx_id": str(dPrescription['id']),
					"step": 0
				})
				oExpiring.create(conflict='replace')

			# Store the medication name
			dRet['medication'] = dPrescription['display']
			dRet['pharmacy'] = dPrescription['pharmacy']
			dRet['ds_id'] = dPrescription['id']

			# Add it to the list
			lRet.append(DictHelper.clone(dRet))

		# Return success
		return {"status": True, "data": lRet}
