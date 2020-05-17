# coding=utf8
""" CSR Service

Handles all CSR requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "chris@fuelforthefire.ca"
__created__		= "2020-05-17"

# Pip imports
from RestOC import Conf, DictHelper, Errors, Services

# Service imports
from .records import TemplateEmail, TemplateSMS

class CSR(Services.Service):
	"""CSR Service class

	Service for CSR access

	Extends: shared.Services.Service
	"""

	_install = [TemplateEmail, TemplateSMS]
	"""Record types called in install"""

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
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

	def template_create(self, data, sesh, _class):
		"""Template Create

		Create a new template of the passed type

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request
			_class {class} -- The class to use

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		#oEff = Services.read('auth', 'verify', {
		#	"name": "csr_templates",
		#	"right": Rights.CREATE
		#}, sesh)
		#if not oEff.data:
		#	return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['title', 'content'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Validate by creating a Record instance
		try:
			oTemplate = _class(data)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the row and return the result
		return Services.Effect(
			oTemplate.create()
		)

	def template_delete(self, data, sesh, _class):
		"""Template Delete

		Delete an existing template for the passed type

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request
			_class {class} -- The class to use

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		#oEff = Services.read('auth', 'verify', {
		#	"name": "csr_templates",
		#	"right": Rights.DELETE
		#}, sesh)
		#if not oEff.data:
		#	return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# If the record does not exist
		if not _class.exists(data['_id']):
			return Services.Effect(error=1104)

		# Delete the record
		if not _class.deleteGet(data['_id']):
			return Services.Effect(error=1102)

		# Return OK
		return Services.Effect(True)

	def template_read(self, data, sesh, _class):
		"""Template Read

		Fetches an existing template of the passed type

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request
			_class {class} -- The class to use

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		#oEff = Services.read('auth', 'verify', {
		#	"name": "csr_templates",
		#	"right": Rights.READ
		#}, sesh)
		#if not oEff.data:
		#	return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the template
		dTemplate = _class.get(data['_id'], raw=True)

		# If it doesn't exist
		if not dTemplate:
			return Services.Effect(error=1104)

		# Return the template
		return Services.Effect(dTemplate)

	def template_update(self, data, sesh, _class):
		"""Template Update

		Updated an existing template of the passed type

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request
			_class {class} -- The class to use

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		#oEff = Services.read('auth', 'verify', {
		#	"name": "csr_templates",
		#	"right": Rights.UPDATE
		#}, sesh)
		#if not oEff.data:
		#	return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Fetch the template
		oTemplate = _class.get(data['_id'])

		# If it doesn't exist
		if not oTemplate:
			return Services.Effect(error=1104)

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']

		# Step through each field passed and update/validate it
		lErrors = []
		for f in data:
			try: oTemplate[f] = data[f]
			except ValueError as e: lErrors.append(e.args[0])

		# If there was any errors
		if lErrors:
			return Services.Effect(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Effect(
			oTemplate.save()
		)

	def templates_read(self, data, sesh, _class):
		"""Templates Read

		Fetches all existing templates of the passed type

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request
			_class {class} -- The class to use

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		#oEff = Services.read('auth', 'verify', {
		#	"name": "csr_templates",
		#	"right": Rights.READ
		#}, sesh)
		#if not oEff.data:
		#	return Services.Effect(error=Rights.INVALID)

		# Fetch and return the templates
		return Services.Effect(
			_class.get(raw=True, orderby=['title'])
		)

	def templateEmail_create(self, data, sesh):
		"""Template Email Create

		Create a new email template

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.template_create(data, sesh, TemplateEmail)

	def templateEmail_delete(self, data, sesh):
		"""Template Email Delete

		Delete an existing email template

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.template_delete(data, sesh, TemplateEmail)

	def templateEmail_read(self, data, sesh):
		"""Template Email Read

		Fetches an existing email template

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.template_read(data, sesh, TemplateEmail)

	def templateEmail_update(self, data, sesh):
		"""Template Email Update

		Updated an existing email template

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.template_update(data, sesh, TemplateEmail)

	def templateEmails_read(self, data, sesh):
		"""Template Emails

		Fetches all existing email templates

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.templates_read(data, sesh, TemplateEmail)

	def templateSms_create(self, data, sesh):
		"""Template Sms Create

		Create a new sms template

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.template_create(data, sesh, TemplateSMS)

	def templateSms_delete(self, data, sesh):
		"""Template Sms Delete

		Delete an existing sms template

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.template_delete(data, sesh, TemplateSMS)

	def templateSms_read(self, data, sesh):
		"""Template Sms Read

		Fetches an existing sms template

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.template_read(data, sesh, TemplateSMS)

	def templateSms_update(self, data, sesh):
		"""Template Sms Update

		Updated an existing sms template

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.template_update(data, sesh, TemplateSMS)

	def templateSmss_read(self, data, sesh):
		"""Template SMSs

		Fetches all existing sms templates

		Arguments:
			data {mixed} -- Data sent with the request
			sesh {Sesh._Session} -- The session associated with the request

		Returns:
			Services.Effect
		"""
		return self.templates_read(data, sesh, TemplateSMS)
