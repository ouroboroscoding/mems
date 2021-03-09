# coding=utf8
""" Link Service

Handles all Documentation requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2021-03-08"

# Pip imports
import arrow
from RestOC import Conf, DictHelper, Errors, JSON, Record_MySQL, \
					Services, StrHelper
import validators

# Shared imports
from shared import Rights

# Records imports
from records.link import UrlRecord, ViewRecord

class Link(Services.Service):
	"""Link Service class

	Service for Documentation
	"""

	_install = [UrlRecord, ViewRecord]
	"""Record types called in install"""

	_codeChars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
	"""Characters used to generate the url code"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Auth
		"""

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

		# Go through each Record type
		for o in cls._install:

			# Install the table
			if not o.tableCreate():
				print("Failed to create `%s` table" % o.tableName())

		# Return OK
		return True

	def stats_read(self, data, sesh=None):
		"""Stats Read

		Create a new Error record

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): Optional, the session associated with the request

		Returns:
			Services.Response
		"""

		# If we have an internal key
		if '_internal_' in data:

			# Verify the key, remove it if it's ok
			if not Services.internalKey(data['_internal_']):
				return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
			del data['_internal_']

		# Else, check permissions
		else:

			# If there's no session
			if not sesh:
				return Services.Error(Errors.REST_AUTHORIZATION)

			# Make sure the user has the proper rights
			Rights.check(sesh, 'link', Rights.READ)

		# If we have a code
		if 'code' in data:

			# Find the URL
			dUrl = UrlRecord.filter({"code": data['code']}, raw=['_id'], limit=1)

			# If it doesn't exist
			if not dUrl:
				return Services.Error(1104)

			# Store the ID
			data['_id'] = dUrl['_id']

		# Else, if we're missing the ID
		elif '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Fetch the views by ID
		lViews = ViewRecord.filter({"url_id": data['_id']}, raw=True, orderby='date')

		# Return as is for now
		return Services.Response(lViews)

	def view_create(self, data):
		"""View Create

		Create a new view associated with the code and return the URL

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If we don't have an internal key
		if '_internal_' not in data:
			return Services.Error(Rights.INVALID)

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Verify fields
		try: DictHelper.eval(data, ['code', 'ip', 'agent'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the URL by code
		oUrl = UrlRecord.filter({"code": data['code']}, limit=1)

		# If it doesn't exist
		if not oUrl:
			return Services.Error(1104)

		# Generate a new date
		oDT = arrow.get()

		# Create a new view instance to check for errors
		try:
			oView = ViewRecord({
				"url_id": oUrl['_id'],
				"date": oDT.format('YYYY-MM-DD'),
				"time": oDT.format('HH:mm:ss'),
				"ip": data['ip'],
				"agent": data['agent']
			})
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Create the new view
		oView.create()

		# Increment the count
		oUrl.incrementView()

		# Return the URL
		return Services.Response(oUrl['url'])

	def url_create(self, data, sesh):
		"""Url Create

		Creates a new link

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'link', Rights.CREATE)

		# If the URL is missing
		if 'url' not in data:
			return Services.Error(1001, [['url', 'missing']])

		# If the url is invalid
		if validators.url(data['url']) != True:
			return Services.Error(1001, [['url', 'invalid']])

		# If the permanent flag is missing
		if 'permanent' not in data:
			data['permanent'] = False

		# Create a new url instance to check for errors
		try:
			oUrl = UrlRecord({
				"code": StrHelper.random(6, self._codeChars),
				"url": data['url'],
				"permanent": data['permanent']
			})
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Loop until we find a usable random key
		while True:
			try:
				oUrl.create()
				break
			except Record_MySQL.DuplicateException:
				oUrl['code'] = StrHelper.random(6, self._codeChars)

		# Return the ID and code used
		return Services.Response({
			"_id": oUrl['_id'],
			"code": oUrl['code']
		})

	def url_delete(self, data, sesh):
		"""Url Create

		Creates a new link

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'link', Rights.DELETE)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the record
		oUrl = UrlRecord.get(data['_id'])

		# If it doesn't exist
		if not oUrl:
			return Services.Error(1104)

		# Delete all views associated
		ViewRecord.deleteByUrl(data['_id'])

		# Delete the record and return the result
		return Services.Response(
			oUrl.delete()
		)

	def urls_read(self, data, sesh):
		"""Url Create

		Creates a new link

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper rights
		Rights.check(sesh, 'link', Rights.READ)

		# Fetch all the urls in the system and return them
		return Services.Response(
			UrlRecord.get(raw=True, orderby='url')
		)
