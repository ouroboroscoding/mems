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

# TemplateEmail structure and config
_mdTemplateEmailConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/csr/template_email.json'),
	'mysql'
)

# TemplateSMS structure and config
_mdTemplateSMSConf = Record_MySQL.Record.generateConfig(
	Tree.fromFile('../definitions/csr/template_sms.json'),
	'mysql'
)

# TemplateEmail class
class TemplateEmail(Record_MySQL.Record):
	"""TemplateEmail

	Represents an email template

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdTemplateEmailConf

# TemplateSMS class
class TemplateSMS(Record_MySQL.Record):
	"""TemplateSMS

	Represents an SMS template

	Extends: RestOC.Record_MySQL.Record
	"""

	@classmethod
	def config(cls):
		"""Config

		Returns the configuration data associated with the record type

		Returns:
			dict
		"""
		return _mdTemplateSMSConf
