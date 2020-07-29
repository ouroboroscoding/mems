# coding=utf8
""" Excel

Shared functionality to deal with parsing / writing excel workbooks
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-07-28"

# Pip imports
import xlrd

STRING = 0
DATETIME = 1
DATE = 2
INTEGER = 3

def _convert_date(val):
	"""Convert Date

	Takes an excel date value turns it into YYYY-MM-DD

	Args:
		val {str} -- The date to convert

	Returns:
		str
	"""

	# Turn the value into a tuple
	tDate = xlrd.xldate_as_tuple(val, 0)

	# Rebuild and return
	return '%d-%02d-%02d' % (
		tDate[0],
		tDate[1],
		tDate[2]
	)

def _convert_datetime(val):
	"""Convert Date Time

	Takes an excel date value turns it into YYYY-MM-DD HH:mm:ss

	Args:
		val {str} -- The date to convert

	Returns:
		str
	"""

	# Turn the value into a tuple
	tDate = xlrd.xldate_as_tuple(val, 0)

	# Rebuild and return
	return '%d-%02d-%02d %02d:%02d:%02d' % (
		tDate[0],
		tDate[1],
		tDate[2],
		tDate[3],
		tDate[4],
		tDate[5]
	)

def parse(filename, conf, sheet=0, start_row=0):
	"""Parse

	Opens a workbook, loads the given sheet (int for by index, str for by name)
	and loads the fields given by the config into dicts, returning them in a
	list

	Arguments:
		filename (str): The name of the workbook file to open
		conf (dict): A dictionary of names to 'column' and 'type'
		sheet (uint|str): Fetch the sheet by index or by name
		start_row (uint): The first row with data, useful for skipping headers

	Returns:
		dict[]
	"""

	# Init the return list of values
	lRet = []

	# Load the file
	oXLS = xlrd.open_workbook(sFilename)

	# If we have an int
	if isinstance(sheet, int):
		oSheet = oXLS.sheet_by_index(sheet)
	else:
		oSheet = oXLS.sheet_by_name(sheet)

	# Go through each row in the sheet
	for i in range(start_row, oSheet.nrows):

		# Init the new row
		dRow = {}

		# Go through each item in the conf
		for k,d in conf.items():

			# If the type is a string
			if d['type'] == STRING:
				dRow[k] = oSheet.cell_value(i, d['column'])

			# Else if it's a date/time
			elif d['type'] == DATETIME:
				dRow[k] = _convert_datetime(oSheet.cell_value(i, d['column']))

			# Else if it's a date
			elif d['type'] == DATE:
				dRow[k] = _convert_date(oSheet.cell_value(i, d['column']))

			# Else if it's an integer
			elif d['type'] == INTEGER:
				dRow[k] = int(oSheet.cell_value(i, d['column']))

			# Else
			else:
				raise ValueError('Uknown conf type: %s' % str(d['type']))

		# Add the row to the return list
		lRet.append(dRow)

	# Return the data found
	return lRet
