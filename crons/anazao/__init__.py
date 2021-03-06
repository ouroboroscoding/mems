# coding=utf8
"""Anazao

Handles incoming data related to anazao
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-08-10"

def run(kind):
	"""Run

	Entry point into the script

	Arguments:
		kind (str): The kind of process to run

	Returns:
		bool
	"""

	# If the type is shipped
	if kind == 'shipped':
		from . import shipped
		return shipped.run()

	# Else, invalid type
	else:
		print('invalid anazao type: %s' % type_)
		return False
