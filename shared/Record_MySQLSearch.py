# coding=utf8
""" Search

Shared functionality to deal with search
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-10-18"

# Pip imports
from RestOC import Record_MySQL

class Record(Record_MySQL.Record):
	"""Record

	Extends the Record_MySQL Record class to add a search method
	"""

	@classmethod
	def search(cls, fields, raw=None, orderby=None, limit=None, custom={}):
		"""Search

		Takes values and converts them to something usable by the filter method

		Arguments:
			fields (dict): A dictionary of field names to the values they
				should match
			raw (bool|list): Return raw data (dict) for all or a set list of
				fields
			orderby (str|str[]): A field or fields to order the results by
			limit (int|tuple): The limit and possible starting point
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			Record[]|dict[]
		"""

		# Init a new list of fields
		dFields = {}

		# Go through each field passed
		for k,d in fields.items():

			# If we got a string
			if isinstance(d, str):
				d = {"value": d, "type": 'exact'}

			elif not isinstance(d, dict):
				raise ValueError(k, 'must be dict')

			# Escape special characters
			d['value'] = d['value'].replace('_', r'\_').replace('%', r'\%')

			# If we're looking for an exact match
			if d['type'] == 'exact':
				dFields[k] = d['value']

			# If it starts with
			elif d['type'] == 'start':
				dFields[k] = {"like": '%s%%' % d['value']}

			# If it ends with
			elif d['type'] == 'end':
				dFields[k] = {"like": '%%%s' % d['value']}

			# If it's a custom lookup
			elif d['type'] == 'asterisk':
				dFields[k] = {"like": d['value'].replace('*', '%')}

			# If it's greater than
			elif d['type'] == 'greater':
				dFields[k] = {"gte": d['value']}

			# If it's less than
			elif d['type'] == 'less':
				dFields[k] = {"lte": d['value']}

			# Else
			else:
				raise ValueError(k, 'invalid type')

		# Pass the newly generate fields to filter and return the result
		return cls.filter(dFields, raw=raw, orderby=orderby, limit=limit, custom=custom)
