# coding=utf8
"""WellDyneRX Incoming Reports

Parses incoming reports from WellDyneRX to place the data in the DB
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-09-01"

# Python imports
import os, platform, sys

# Pip imports
import arrow
import pysftp
from RestOC import Conf, Record_MySQL

# Shared imports
from shared import Excel

# Record imports
from records.monolith import ShippingInfo

# Only run if called directly
if __name__ == "__main__":

	# Load the config
	Conf.load('config.json')
	sConfOverride = 'config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Add hosts
	Record_MySQL.addHost('monolith', Conf.get(("mysql", "hosts", "monolith")))

	# List of dates
	lDays = ['080820', '080920', '081020', '081120', '081220', '081320', '081420',
			'081520', '081620', '081720', '081820', '081920', '082020', '082120',
			'082220', '082320', '082420', '082520', '082620', '082720', '082820',
			'082920', '083020']

	# Get the sFTP and temp file conf
	dSftpConf = Conf.get(('welldyne', 'sftp'))
	sTemp = Conf.get(('temp_folder'))

	# Go through each date
	for sDay in lDays:

		# Generate the name of the file
		sFilename = 'MaleExcel_DailyShippedOrders_%s.xlsx' % sDay

		# Connect to the sFTP
		with pysftp.Connection(dSftpConf['host'], username=dSftpConf['username'], password=dSftpConf['password']) as oCon:

			# Get the outreach file
			try:
				print('Fetching %s' % sFilename)
				sGet = '%s/%s' % (sTemp, sFilename)
				oCon.get('processed/%s' % sFilename, sGet)
			except FileNotFoundError:
				print('%s file not found on sFTP' % sFilename)
				sys.exit(1)

		# Parse the data
		lData = Excel.parse(sGet, {
			"shipped": {"column": 1, "type": Excel.DATETIME},
			"tracking": {"column": 3, "type": Excel.STRING},
			"rx": {"column": 7, "type": Excel.INTEGER},
			"member_id": {"column": 17, "type": Excel.STRING}
		}, start_row=1)

		# Go through each one and keep only uniques
		dData = {}
		for d in lData:
			d['customerId'] = d['member_id'].lstrip('0')
			dData[d['customerId']] = d
		lData = list(dData.values())

		# Get date/time
		sDT = arrow.get().format('YYYY-MM-DD HH:mm:ss')

		# Go through each code and store it in the DB
		for d in lData:
			print('Working on %s... ' % d['tracking'], end='')
			oShippingInfo = ShippingInfo({
				"code": d['tracking'],
				"customerId": d['customerId'],
				"date": d['shipped'][0:10],
				"type": d['tracking'][0:2] == '1Z' and 'UPS' or 'USPS',
				"createdAt": sDT,
				"updatedAt": sDT
			})
			sID = oShippingInfo.create(conflict='ignore')
			print('%s' % str(sID))

		# Delete the file
		os.remove(sGet)
