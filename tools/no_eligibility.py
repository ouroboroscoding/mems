# coding=utf8
"""No Eligibility

Creates a list of patients that should be removed from welldyne
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-11-18"

# Python imports
import os
import platform
import sys

# Pip imports
from RestOC import Conf, Record_Base, Record_MySQL

# Record imports
from records.welldyne import Eligibility

# Load the config
Conf.load('config.json')
sConfOverride = 'config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add the global prepend and primary host to mysql
Record_Base.dbPrepend(Conf.get(("mysql", "prepend"), ''))
Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith_read")))

# Start the new list
lLines = []

# Open the initial eligibility file
with open(sys.argv[1], 'r') as oIn:

	# Open the file to write to
	with open('./NO_ELIGIBILITY.TXT', 'w') as oOut:

		# Init count
		iCount = 0

		# Go through each line
		for sLine in oIn:

			iCount += 1
			print('\r%d' % iCount, end='')

			# Get the member ID
			sMember = sLine[15:21].lstrip('0')

			# Check eligibility
			dElig = Eligibility.filter({"customerId": sMember}, raw=True, limit=1)

			# If we have none, or it's 0000-00-00
			if not dElig or dElig['memberThru'] == '0000-00-00 00:00:00':

				# Generate the line
				sLine = '%s%s%s' % (sLine[0:313], '20200601', sLine[321:])

				# Add to the output
				oOut.write(sLine)
				oOut.flush()

print(' done')
