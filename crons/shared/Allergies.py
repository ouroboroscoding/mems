# coding=utf8
"""Allergies

Get the allergies for a specific customer
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-03"

# Service imports
from records.monolith import TfLanding, TfAnswer

# AutoCorrect
AUTOCORRECT = {
	"Amoxicillin": [
		'amoxicillin', 'amoxasilin', 'amoxicilin', 'amoxicillan',
		'amoxicillian', 'amoxicillin,', 'amoxycillan'
	],
	"Aspirin": [
		'aspirin', 'asprin', 'asa', 'aprin', 'asperin', 'aspirin,', 'aspirina',
		'aspren'
	],
	"Bactrim": [
		'bactrim', 'bactrium', 'bactrom', 'bactrum', 'bactum', 'batrim'
	],
	"Benadryl": [
		'benadryl', 'benadril', 'benedryl'
	],
	"Ciprofloxacin": [
		'ciprofloxacin', 'cipro', 'ciprol'
	],
	"Codeine": [
		'codeine', 'codine', 'codean', 'codeen', 'codein', 'codeine', 'coden',
		'codene', 'codien', 'codiene', 'codin', 'codine', 'coding', 'coedine'
	],
	"Demerol": [
		'demerol', 'demeral', 'demoral'
	],
	"Ibuprofen": [
		'ibuprofen', 'ibprofen', 'ibpurofen', 'ibu', 'ibuprophen'
	],
	"Keflex": [
		'keflex', 'kflex'
	],
	"Lisinopril": [
		'lisinopril', 'lasinaprel', 'linsinpril', 'lisinapril', 'lisinipril',
		'lisiniprol', 'lisinopril,', 'lisinoprill', 'lisinoprol', 'lisinpril',
		'lisinprol'
	],
	"Metformin": [
		'metformin', 'met forman', 'metform', 'metforman'
	],
	"Morphine": [
		'morphine', 'mophine', 'morfine', 'moriphine', 'morphene', 'morphin',
		'morpine'
	],
	"Naproxen": [
		'naproxen', 'naproxen sodium', 'naproxen’s', 'naproxin'
	],
	"Ninguno": [
		'ninguno', 'niguno', 'ninguna'
	],
	"None": [
		'none', '', 'no', 'non', 'nine', 'nome', 'nonr', 'nonw', '"none"',
		'none\\', 'none\'', 'none.', 'nono', 'mone', 'nothing', 'not', 'n/a',
		'na', 'n', '0', 'no allergies', 'do not have any', 'nope', 'nnone',
		'noen', 'none known', 'nobe', 'no\\', 'don\'t have any', 'nonee',
		'none \\', 'no e', 'npne', 'not have any', 'n0ne', 'nonenone', 'n one',
		'noe', 'none ', 'none]', 'none \'', 'mome', 'i do not have any',
		'none .', 'nonoe', 'none that i know of', 'nne', 'noned', '.none',
		'nane', '`none', 'nonew', 'noone', 'noon', 'nont', 'non e', 'nun',
		'dont have any', 'nonne', 'no ne', 'no tengo', 'mo', 'nada',
		'no allergy', 'none,', 'nione', 'nona', 'nil', 'no one', 'none!',
		'none of', 'enter none', 'nio', 'n9ne', 'nkda', 'nka'
	],
	"Oxycodone": [
		'oxycodone', 'oxycontin', 'oxycotton'
	],
	"Penicillin": [
		'penicillin', 'penicillian', 'penicillan', 'penicilin', 'penecillin',
		'penecilin', 'pencillin', 'penisilin', 'pennicillin', 'penicilian',
		'penacilin', 'pencillian', 'penacillin', 'penicillon', 'penicilina',
		'pencilian', 'penecillian', 'penicillin,', 'penicillen', 'penicilan',
		'pincillin', 'penecillan', 'peniciline', 'penicillins', 'penacillian',
		'penisillin', 'allergic to penicillin', 'penicillion', 'peneciline',
		'pennicilin', 'penn', 'pennicillen', 'pennicillan', 'penacylin',
		'penasilin', 'penosilin', 'penesilin', 'penicllin', 'penaciline',
		'pinacillin', 'pennicillian', 'piniscillon', 'pinicillin', 'pennecilin',
		'peninsula', 'pencilen', 'penacillen', 'penciling', 'pencillan',
		'penacillon', 'penacilan', 'pencilin', 'pennacilin', 'pen.', 'pinisilin',
		'penicilion', 'pennicellin', 'penacilion', 'penincillin', 'peninsulyn',
		'pencilling', 'penasillin', 'pennicilan', 'penacilen', 'penicillin.',
		'pennisilym', 'penecilan', 'pinacelin', 'pencilllin', 'pinaclin',
		'penincilin', 'penasilen', 'pinasilin', 'penncillen', 'peniccilin',
		'pencil', 'penicillun', 'penicylin', 'pencllin', 'penacillion',
		'peninsilyn', 'penecilen', 'pennicilen', 'pinacillan', 'pinacelen',
		'penicilline', 'penicilla', 'pencile', 'penisilon', 'penacillan',
		'penniclen', 'pennacillin', 'penaclin', 'penecillion', 'penacilon',
		'pinisilon', 'pinisillon', 'peniclin', 'penciline', 'pencillen',
		'pinacilen'
	],
	"Percocet": [
		'percocet', 'percoset'
	],
	"Sulfa": [
		'sulfa', 'sufer', 'suffer', 'sulfa antibiotics', 'sulfa based medicine',
		'sulfa drug', 'sulfa drugs', 'sulfa meds', 'sulfa,', 'sulfas', 'sulpha'
	],
	"Tetracycline": [
		'tetracycline', 'tetracyclene'
	],
	"Tramadol": [
		'tramadol', 'tremidal'
	],
	"Vicodin": [
		'vicodin', 'vicadin', 'vicoden',
	]
}

def fetch(data):
	"""Fetch

	Attempts to find the allergies for the given customer

	Arguments:
		data (dict): Data associated with the customer

	Returns:
		str
	"""

	# Try to find a landing for the customer
	lLanding = TfLanding.find(
		data['last'],
		data['email'] or '',
		data['phone'] or '',
		['MIP-A1', 'MIP-A2', 'MIP-H1', 'MIP-H2']
	)

	# If we have any
	if lLanding:

		# Look for answers for the specific questions
		dAnswers = {
			d['ref']:d['value'] for d in TfAnswer.filter({
				"landing_id": lLanding[0]['landing_id'],
				"ref": ['95f9516a-4670-43b1-9b33-4cf822dc5917', 'allergies', 'allergiesList']
			}, raw=['ref', 'value'])
		}

		# If we have an allergiesList
		if 'allergiesList' in dAnswers:
			sAnswer = dAnswers['allergiesList']
		elif 'allergies' in dAnswers:
			sAnswer = dAnswers['allergies']
		elif '95f9516a-4670-43b1-9b33-4cf822dc5917' in dAnswers:
			sAnswer = dAnswers['95f9516a-4670-43b1-9b33-4cf822dc5917']
		else:
			sAnswer = None

		# If we have an answer
		if sAnswer:

			# If the answer is valid
			if sAnswer in AUTOCORRECT:
				return sAnswer

			# Else, go through the autocorrect
			else:
				s = sAnswer.strip().lower();
				for k in AUTOCORRECT:
					if s in AUTOCORRECT[k]:
						sAnswer = k
						break

				# Push the answer to the row
				return sAnswer

		# If we got nothing, assume None
		else:
			return 'None'

	# No landing found
	else:
		return ''
