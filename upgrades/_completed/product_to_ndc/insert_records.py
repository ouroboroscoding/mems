# coding=utf8
""" Insert the ED products"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Insert the records
	Record_MySQL.Commands.execute(
		'primary',
		"INSERT INTO `mems`.`prescriptions_product` "\
		"(`_id`, `pharmacy`, `key`, `display`, `ndc`, `quantity`, `supply`, `directions`, `unit_id`) " \
		"VALUES " \
		"(UUID(), 'WellDyneRX', 'tadalafil_5mg_30p_30d', 'Tadalafil 5mg Tablet', '00093301756', '30', '30', '1 tab po qday!', '26'), " \
		"(UUID(), 'WellDyneRX', 'sildenafil_100mg_6p_30d', 'Sildenafil 100 mg tablet', '00093534301', '6', '30', 'Take one tab by mouth once daily 60 minutes prior to sexual activity as needed.', '26'), " \
		"(UUID(), 'WellDyneRX', 'sildenafil_50mg_6p_30d', 'Sildenafil 100 mg tablet', '00093534301', '6', '30', 'Initial dose patient to cut tab in half to take 50mg by mouth qday 60 mins prior to sexual activity. May increase to 100mg qday as tolerated', '26'), " \
		"(UUID(), 'WellDyneRX', 'tadalafil_20mg_6p_30d', 'Tadalafil 20mg Tablet', '69238134903', '6', '30', '1 tablet 3-4 hours before sexual activity as needed.  Maximum dose is 1 pill every 3 days.', '26');"
	)

	# Return OK
	return True
