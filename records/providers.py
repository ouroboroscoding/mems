# coding=utf8
""" Providers Records

Handles the record structures for the Providers service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-10-15"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# Provider class
class Provider(Record_MySQL.Record):
	"""Provider

	Represents a memo user in mems
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
				Tree.fromFile('definitions/providers/provider.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# TemplateEmail class
class TemplateEmail(Record_MySQL.Record):
	"""TemplateEmail

	Represents an email template
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
				Tree.fromFile('definitions/providers/tpl_email.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

# TemplateSMS class
class TemplateSMS(Record_MySQL.Record):
	"""TemplateSMS

	Represents an SMS template
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
				Tree.fromFile('definitions/providers/tpl_sms.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
