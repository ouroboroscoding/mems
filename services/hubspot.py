# coding=utf8
""" HubSpot Service

Handles all HubSpot requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-11-12"

# Pip imports
from RestOC import Conf, DictHelper, Services

class HubSpot(Services.Service):
	"""HubSpot Service class

	Service for HubSpot CRM access
	"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Store config data
		self._key = Conf.get(('hubspot', 'api_key'))

		# Return self for chaining
		return self

	@classmethod
	def install(cls):
		"""Install

		The service's install method, used to setup storage or other one time
		install configurations

		Returns:
			bool
		"""
		return True
