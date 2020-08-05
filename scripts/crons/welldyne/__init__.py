# coding=utf8
"""WellDyneRX

Handles all reports, ingoing and outgoing, related to WellDyneRX
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-07-16"

def run(type, report, arg1=None):
	"""Run

	Entry point into the script

	Arguments:
		type (str): The type of report to parse
		arg1 (str): Possible data passed to the report

	Returns:
		int
	"""

	# If the type is adhoc
	if type == 'adhoc':
		from . import adhoc
		return adhoc.run(report)

	# Else, if the type is outgoing
	elif type == 'outgoing':
		from . import outgoing
		return outgoing.run(report, arg1)

	# Else if the type is incoming
	elif type == 'incoming':
		from . import incoming
		return incoming.run(report, arg1)

	# Else, invalid type
	else:
		print('invalid welldyne type: %s' % type)
		return False
