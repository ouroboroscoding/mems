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

def run(kind, report, arg1=None):
	"""Run

	Entry point into the script

	Arguments:
		kind (str): The kind of report to parse
		arg1 (str): Possible data passed to the report

	Returns:
		bool
	"""

	# Else if the type is eligibility
	if kind == 'eligibility':
		from . import eligibility
		return eligibility.run(report)

	# Else if the type is incoming
	elif kind == 'incoming':
		from . import incoming
		return incoming.run(report, arg1)

	# Else, if the type is outgoing
	elif kind == 'outgoing':
		from . import outgoing
		return outgoing.run(report, arg1)

	# Else, invalid type
	else:
		print('invalid welldyne report: %s' % report)
		return False
