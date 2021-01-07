# coding=utf8
""" Insert the calendly events"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Insert the records
	Record_MySQL.Commands.execute(
		'monolith',
		"INSERT INTO `monolith`.`calendly_event` "\
		"(`name`, `uri`, `type`, `state`, `provider`) " \
		"VALUES " \
		"('Charlotte In Person Visit', '/male-excel-hrt/charlotte-in-person-visit', 'hrt', 'NC', NULL), " \
		"('Dr. Mark Matthews Follow Up', '/male-excel-hrt/dr-mark-matthews-refill', 'hrt', NULL, '111'), " \
		"('Elizabeth Hernandez Follow up', '/male-excel-hrt/hernandez-followup', 'hrt', NULL, '46'), " \
		"('Underwood Follow-Up', '/male-excel-hrt/tony-underwood-refill', 'hrt', NULL, '104'), " \
		"('Alabama Video Consult', '/male-excel-hrt/alabama', 'hrt', 'AL', NULL), " \
		"('Alaska Video Consult', '/male-excel-hrt/alaska', 'hrt', 'AK', NULL), " \
		"('Arizona Video Consult', '/male-excel-hrt/arizona', 'hrt', 'AZ', NULL), " \
		"('Arkansas Video Consult', '/male-excel-hrt/arkansas', 'hrt', 'AR', NULL), " \
		"('California Video Consult', '/male-excel-hrt/california', 'hrt', 'CA', NULL), " \
		"('Colorado Video Consult', '/male-excel-hrt/colorado', 'hrt', 'CO', NULL), " \
		"('Connecticut Video Consult', '/male-excel-hrt/connecticut', 'hrt', 'CT', NULL), " \
		"('Delaware Video Consult', '/male-excel-hrt/delaware', 'hrt', 'DE', NULL), " \
		"('Florida Video Consult', '/male-excel-hrt/florida', 'hrt', 'FL', NULL), " \
		"('Georgia Video Consult', '/male-excel-hrt/georgia', 'hrt', 'GA', NULL), " \
		"('Hawaii Video Consult', '/male-excel-hrt/hawaii', 'hrt', 'HI', NULL), " \
		"('Idaho Video Consult', '/male-excel-hrt/idaho', 'hrt', 'ID', NULL), " \
		"('Illinois Video Consult', '/male-excel-hrt/illinois', 'hrt', 'IL', NULL), " \
		"('Indiana Video Consult', '/male-excel-hrt/indiana', 'hrt', 'IN', NULL), " \
		"('Iowa Video Consult', '/male-excel-hrt/iowa', 'hrt', 'IA', NULL), " \
		"('Kansas Video Consult', '/male-excel-hrt/kansas', 'hrt', 'KS', NULL), " \
		"('kentucky Video Consult', '/male-excel-hrt/kentucky', 'hrt', 'KY', NULL), " \
		"('Louisiana Video Consult', '/male-excel-hrt/louisiana', 'hrt', 'LA', NULL), " \
		"('Maine Video Consult', '/male-excel-hrt/maine', 'hrt', 'ME', NULL), " \
		"('Maryland Video Consult', '/male-excel-hrt/maryland', 'hrt', 'MD', NULL), " \
		"('Massachusetts Video Consult', '/male-excel-hrt/massachusetts', 'hrt', 'MA', NULL), " \
		"('Michigan Video Consult', '/male-excel-hrt/michigan', 'hrt', 'MI', NULL), " \
		"('Minnesota Video Consult', '/male-excel-hrt/minnesota', 'hrt', 'MN', NULL), " \
		"('Mississippi Video Consult', '/male-excel-hrt/mississippi', 'hrt', 'MS', NULL), " \
		"('Missouri Video Consult', '/male-excel-hrt/missouri', 'hrt', 'MO', NULL), " \
		"('Montana Video Consult', '/male-excel-hrt/montana', 'hrt', 'MT', NULL), " \
		"('Nebraska Video Consult', '/male-excel-hrt/nebraska', 'hrt', 'NE', NULL), " \
		"('Nevada Video Consult', '/male-excel-hrt/nevada', 'hrt', 'NV', NULL), " \
		"('New Hampshire Video Consult', '/male-excel-hrt/new-hampshire', 'hrt', 'NH', NULL), " \
		"('New Jersey Video Consult', '/male-excel-hrt/new-jersey', 'hrt', 'NH', NULL), " \
		"('New Mexico Video Consult', '/male-excel-hrt/new-mexico', 'hrt', 'NM', NULL), " \
		"('New York Video Consult', '/male-excel-hrt/new-york', 'hrt', 'NY', NULL), " \
		"('North Carolina Video Consult', '/male-excel-hrt/north-carolina', 'hrt', 'NC', NULL), " \
		"('North Dakota Video Consult', '/male-excel-hrt/north-dakota', 'hrt', 'ND', NULL), " \
		"('Ohio Video Consult', '/male-excel-hrt/ohio', 'hrt', 'OH', NULL), " \
		"('Oklahoma Video Consult', '/male-excel-hrt/oklahoma', 'hrt', 'OK', NULL), " \
		"('Oregon Video Consult', '/male-excel-hrt/oregon', 'hrt', 'OR', NULL), " \
		"('Pennsylvania Video Consult', '/male-excel-hrt/pennsylvania', 'hrt', 'PA', NULL), " \
		"('Rhode Island Video Consult', '/male-excel-hrt/rhode-island', 'hrt', 'RI', NULL), " \
		"('South Carolina Video Consult', '/male-excel-hrt/south-carolina', 'hrt', 'SC', NULL), " \
		"('South Dakota Video Consult', '/male-excel-hrt/south-dakota', 'hrt', 'SC', NULL), " \
		"('Tennessee Video Consult', '/male-excel-hrt/tennessee', 'hrt', 'TN', NULL), " \
		"('Texas Video Consult', '/male-excel-hrt/texas', 'hrt', 'TX', NULL), " \
		"('Utah Video Consult', '/male-excel-hrt/utah', 'hrt', 'UT', NULL), " \
		"('Vermont Video Consult', '/male-excel-hrt/vermont', 'hrt', 'VT', NULL), " \
		"('Virginia Video Consult', '/male-excel-hrt/virginia', 'hrt', 'VA', NULL), " \
		"('Washington Video Consult', '/male-excel-hrt/washington', 'hrt', 'WA', NULL), " \
		"('West Virginia Video Consult', '/male-excel-hrt/west-virginia', 'hrt', 'WV', NULL), " \
		"('Wisconsin Video Consult', '/male-excel-hrt/wisconsin', 'hrt', 'WI', NULL), " \
		"('Wyoming Video Consult', '/male-excel-hrt/wyoming', 'hrt', 'WY', NULL), " \
		"('Dr Peter Fotinos Refill', '/male-excel-hrt/dr-peter-fotinos-1', 'hrt', NULL, '55'), " \
		"('Dr Figg Follow Up', '/male-excel-hrt/hrt-drfigg', 'hrt', NULL, '56'), " \
		"('Idaho Video Consultation', '/support-specialist-scheduling/id', 'ed', 'ID', NULL), " \
		"('New Mexico Video Consultation', '/support-specialist-scheduling/nm', 'ed', 'NM', NULL), " \
		"('New Hampshire Video Consultation', '/support-specialist-scheduling/nh', 'ed', 'NH', NULL), " \
		"('West Virginia Phone Consultation', '/support-specialist-scheduling/wv', 'ed', 'WV', NULL), " \
		"('Indiana Consultation', '/support-specialist-scheduling/in', 'ed', 'IN', NULL), " \
		"('Arizona Phone Consultation', '/support-specialist-scheduling/az', 'ed', 'AZ', NULL), " \
		"('Delaware Video Consultation', '/support-specialist-scheduling/de', 'ed', 'DE', NULL), " \
		"('New Jersey Phone Consultation', '/support-specialist-scheduling/nj', 'ed', 'NJ', NULL), " \
		"('Louisiana Phone Consultation', '/support-specialist-scheduling/la', 'ed', 'LA', NULL), " \
		"('Arkansas Video Consultation', '/support-specialist-scheduling/ar', 'ed', 'AR', NULL), " \
		"('Nevada Video Consultation', '/support-specialist-scheduling/nv', 'ed', 'NV', NULL);"
	)

	# Return OK
	return True

