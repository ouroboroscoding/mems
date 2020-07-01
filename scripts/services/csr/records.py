# coding=utf8
""" CSR Records

Handles the record structures for the CSR service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-05-17"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, Record_MySQL

# EscalateAgent class
class EscalateAgent(Record_MySQL.Record):
	"""EscalateAgent

	Represents an agent that can have issues escalated to them
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
				Tree.fromFile('../definitions/csr/escalate_agent.json'),
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
				Tree.fromFile('../definitions/csr/tpl_email.json'),
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
				Tree.fromFile('../definitions/csr/tpl_sms.json'),
				'mysql'
			)

		# Return the config
		return cls._conf
