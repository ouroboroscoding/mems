# coding=utf8
"""Monolith

Handles all crons related to Memo/Monolith
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-14"

def run(kind):
	"""Run

	Entry point into the script

	Arguments:
		kind (str): The kind of report to parse
		arg1 (str): Possible data passed to the report

	Returns:
		bool
	"""

	# If the type is adhoc
	if kind == 'claims_timeout':
		from . import claims_timeout
		return claims_timeout.run()

	# Else, invalid type
	else:
		print('invalid monolith type: %s' % type_)
		return False
