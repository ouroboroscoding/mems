# coding=utf8
""" Reports Records

Handles the record structures for the Reports service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-08-22"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# LastRun class
class LastRun(Record_MySQL.Record):
	"""Last Run

	Represents a the last time some report was run, useful for cron jobs that
	need to fetch
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""

		# If we haven loaded the config yet
		if not cls._conf:
			cls._conf = Record_MySQL.Record.generateConfig(
				Tree.fromFile('definitions/reports/last_run.json'),
				'mysql'
			)

		# Return the config
		return cls._conf


# Recipients class
class Recipients(Record_MySQL.Record):
	"""Recipients

	Represents a single report and all receipients of it
	"""

	_conf = None
	"""Configuration"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""

		# If we haven loaded the config yet
		if not cls._conf:
			cls._conf = Record_MySQL.Record.generateConfig(
				Tree.fromFile('definitions/reports/recipients.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
