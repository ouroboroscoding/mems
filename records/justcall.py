# coding=utf8
""" JustCall Records

Handles the record structures for the JustCall service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2021-06-24"

# Pip imports
from FormatOC import Tree
from RestOC import Record_MySQL

# QueueCall class
class QueueCall(Record_MySQL.Record):
	"""Queue Call

	Represents a JustCall queued call
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
				Tree.fromFile('definitions/justcall/queue_call.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# QueueNumber class
class QueueNumber(Record_MySQL.Record):
	"""Queue Number

	Represents a JustCall queue number and it's CS type
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
				Tree.fromFile('definitions/justcall/queue_number.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# MemoId class
class MemoId(Record_MySQL.Record):
	"""Memo ID

	Represents a JustCall agent to their memo counterpart
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
				Tree.fromFile('definitions/justcall/memo_id.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
