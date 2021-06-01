# coding=utf8
""" Link Records

Handles the record structures for the Link service
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2021-03-08"

# Pip imports
from FormatOC import Tree
from RestOC import Conf, JSON, Record_MySQL

# UrlRecord class
class UrlRecord(Record_MySQL.Record):
	"""Url Record

	Represents a url
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
				Tree.fromFile('definitions/link/url.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	def incrementView(self):
		"""Increment View

		Increases the view count by one

		Returns:
			uint
		"""

		# If the record lacks a primary key (never been created/inserted)
		if self._dStruct['primary'] not in self._dRecord:
			raise KeyError(self._dStruct['primary'])

		# Increment the view for the current record
		return Record_MySQL.Commands.execute(
			self._dStruct['host'],
			"UPDATE `%(db)s`.`%(table)s` " \
			"SET `views` = `views` + 1 " \
			"WHERE `%(primary)s` = '%(id)s'" % {
				"db": self._dStruct['db'],
				"table": self._dStruct['table'],
				"primary": self._dStruct['primary'],
				"id": self._dRecord[self._dStruct['primary']]
			}
		)

# ViewRecord class
class ViewRecord(Record_MySQL.Record):
	"""View Record

	Represents a view associated with a url
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
				Tree.fromFile('definitions/link/view.json'),
				'mysql'
			)

		# Return the config
		return cls._conf

	@classmethod
	def deleteByUrl(cls, url_id, custom={}):
		"""Delete By URL

		Deletes all views associated with a url ID

		Arguments:
			url_id (str|str[]): The UUID of the url
			custom (dict): Custom Host and DB info
				'host' the name of the host to get/set data on
				'append' optional postfix for dynamic DBs

		Returns:
			None
		"""

		# If we have one ID

		# Fetch the record structure
		dStruct = cls.struct(custom)

		# Delete the records
		Record_MySQL.Commands.execute(
			dStruct['host'],
			"DELETE FROM `%(db)s`.`%(table)s` WHERE `url_id` %(ids)s" % {
				"db": dStruct['db'],
				"table": dStruct['table'],
				"ids": (isinstance(url_id, list) and \
						("IN ('%s')" % "','".join(url_id)) or \
						("= '%s'" % url_id)),
			}
		)
