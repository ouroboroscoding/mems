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
from RestOC import DictHelper, Errors, Record_MySQL, Services

# Shared imports
from shared import Rights

# Service imports
from records.csr import Agent, CustomList, CustomListItem, TemplateEmail, \
						TemplateSMS

class CSR(Services.Service):
	"""CSR Service class

	Service for CSR access
	"""

	_install = [Agent, TemplateEmail, TemplateSMS]
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

	def _agent_create(self, memo_id, sesh):
		"""Agent Create

		Creates the actual agent record in the DB as well as necessary
		permissions

		Arguments:
			memo_id (uint): The ID of the user in Memo
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Create a new agent instance using the memo ID
		try:
			oAgent = Agent({
				"memo_id": memo_id
			})
		except ValueError:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the agent and store the ID
		try:
			sID = oAgent.create()
		except Record_MySQL.DuplicateException as e:
			return Services.Effect(error=1101)

		# Create the default permissions
		oEff = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": sID,
			"permissions": {
				"csr_claims": 14,
				"csr_messaging": 5,
				"csr_templates": 1,
				"crm_customers": 1,
				"memo_mips": 3,
				"memo_notes": 5,
				"prescriptions": 3,
				"welldyne_adhoc": 4
			}
		}, sesh)
		if oEff.errorExists():
			print(oEff)
			return Services.Effect(sID, warning='Failed to creater permissions for agent')

		# Create the agent and return the ID
		return Services.Effect(sID)

	def _template_create(self, data, sesh, _class):
		"""Template Create

		Create a new template of the passed type

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			_class (class): The class to use

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.CREATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

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

	def _template_delete(self, data, sesh, _class):
		"""Template Delete

		Delete an existing template for the passed type

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			_class (class): The class to use

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.DELETE,
			"ident": data['_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# If the record does not exist
		if not _class.exists(data['_id']):
			return Services.Effect(error=1104)

		# Delete the record
		if not _class.deleteGet(data['_id']):
			return Services.Effect(error=1102)

		# Return OK
		return Services.Effect(True)

	def _template_read(self, data, sesh, _class):
		"""Template Read

		Fetches an existing template of the passed type

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			_class (class): The class to use

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.READ,
			"ident": data['_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Look for the template
		dTemplate = _class.get(data['_id'], raw=True)

		# If it doesn't exist
		if not dTemplate:
			return Services.Effect(error=1104)

		# Return the template
		return Services.Effect(dTemplate)

	def _template_update(self, data, sesh, _class):
		"""Template Update

		Updated an existing template of the passed type

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			_class (class): The class to use

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.UPDATE,
			"ident": data['_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

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

	def _templates_read(self, data, sesh, _class):
		"""Templates Read

		Fetches all existing templates of the passed type

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			_class (class): The class to use

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Fetch and return the templates
		return Services.Effect(
			_class.get(raw=True, orderby=['title'])
		)

	def agent_create(self, data, sesh):
		"""Agent Create

		Creates a user record associated with the memo user in order to apply
		permissions to it

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.CREATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['userName', 'firstName', 'lastName', 'password'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Send the data to monolith to create the memo user
		data['_internal_'] = Services.internalKey()
		oEff = Services.create('monolith', 'user', data, sesh)
		if oEff.errorExists(): return oEff

		# Create the agent record
		return self._agent_create(oEff.data, sesh)

	def agent_delete(self, data, sesh):
		"""Agent Delete

		Deletes an existing memo user record associated

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.DELETE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Find the Agent
		oAgent = Agent.get(data['_id'])

		# Use the memo ID to mark the memo user as inactive
		oEff = Services.update('monolith', 'user/active', {
			"_internal_": Services.internalKey(),
			"id": oAgent['memo_id'],
			"active": False
		}, sesh)
		if oEff.errorExists(): return oEff

		# Delete all permissions
		oEff = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": data['_id'],
			"permissions": {}
		}, sesh);
		if oEff.errorExists(): return oEff

		# Delete the record and return the result
		return Services.Effect(
			oAgent.delete()
		)

	def agent_read(self, data, sesh):
		"""Agent Read

		Fetches one, many, or all user records

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		pass

	def agent_update(self, data, sesh):
		"""Agent Update

		Updates an existing agent (via memo user)

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.UPDATE
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Find the agent
		dAgent = Agent.get(data['_id'], raw=['memo_id'])
		if not dAgent:
			return Services.Effect(error=1104)

		# Remove the agent ID and add the memo one
		del data['_id']
		data['id'] = dAgent['memo_id']

		# Pass the info on to monolith service
		data['_internal_'] = Services.internalKey()
		oEff = Services.update('monolith', 'user', data, sesh)

		# Return whatever monolith returned
		return oEff

	def agentInternal_read(self, data, sesh):
		"""Agent Internal

		Fetches a memo user by their Memo ID rather then their primary key.
		Internal function, can not be used from outside

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_internal_', 'id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Effect(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Look up the record
		dUser = Agent.filter(
			{"memo_id": data['id']},
			raw=True,
			limit=1
		)

		# If there's no such user
		if not dUser:
			return Services.Effect(error=1104)

		# Return the user
		return Services.Effect(dUser)

	def agentPermissions_read(self, data, sesh):
		"""Agent Permissions Read

		Returns all permissions associated with an agent

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['agent_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.READ,
			"ident": data['agent_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Fetch the permissions from the auth service
		oEff = Services.read('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user_id": data['agent_id']
		}, sesh)

		# Return whatever was found
		return oEff

	def agentPermissions_update(self, data, sesh):
		"""Agent Permissions Update

		Updates the permissions associated with an agent

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['agent_id', 'permissions'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.READ,
			"ident": data['agent_id']
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Fetch the permissions from the auth service
		oEff = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": data['agent_id'],
			"permissions": data['permissions']
		}, sesh)

		# Return whatever was found
		return oEff

	def agentNames_read(self, data, sesh):
		"""Agent Names

		Returns the list of agents who can have issues transfered / escalated to
		them

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Fetch all the agents
		lAgents = Agent.get(raw=['memo_id'])

		# Fetch their names
		oEff = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": [d['memo_id'] for d in lAgents]
		}, sesh)

		# Regardless of what we got, retun the effect
		return oEff

	def agents_read(self, data, sesh):
		"""Agents

		Returns all agents in the system

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has the proper permission to do this
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Fetch all the agents
		lAgents = Agent.get(raw=True)

		# Fetch all the Memo user's associated
		oEff = Services.read('monolith', 'users', {
			"_internal_": Services.internalKey(),
			"id": [d['memo_id'] for d in lAgents],
			"fields": ['id', 'userName', 'firstName', 'lastName', 'email', 'dsClinicId', 'dsClinicianId']
		}, sesh)
		if oEff.errorExists(): return oEff

		# Turn it into a dictionary
		dMemoUsers = {d['id']:d for d in oEff.data}

		# Go through each user and find the memo user
		for d in lAgents:
			if d['memo_id'] in dMemoUsers:
				d['userName'] = dMemoUsers[d['memo_id']]['userName']
				d['firstName'] = dMemoUsers[d['memo_id']]['firstName']
				d['lastName'] = dMemoUsers[d['memo_id']]['lastName']
				d['email'] = dMemoUsers[d['memo_id']]['email']
				d['dsClinicId'] = dMemoUsers[d['memo_id']]['dsClinicId']
				d['dsClinicianId'] = dMemoUsers[d['memo_id']]['dsClinicianId']
			else:
				d['userName'] = 'n/a'
				d['firstName'] = 'Not'
				d['lastName'] = 'Found'
				d['email'] = ''
				d['dsClinicId'] = None
				d['dsClinicianId'] = None

		# Return the agents in order of userName
		return Services.Effect(sorted(lAgents, key=lambda o: o['userName']))

	def list_create(self, data, sesh):
		"""List Create

		Create a new custom list

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has at least csr messaging permission
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['title'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Try to make an instance
		try:
			oList = CustomList({
				"agent": sesh['user_id'],
				"title": data['title']
			})
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the row and return the result
		return Services.Effect(
			oList.create()
		)

	def list_delete(self, data, sesh):
		"""List Delete

		Deletes a list and all items

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has at least csr messaging permission
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the list
		oList = CustomList.get(data['_id'])
		if not oList:
			return Services.Effect(error=1104)

		# Make sure the agent owns the list
		if oList['agent'] != sesh['user_id']:
			return Services.Effect(error=1105)

		# Delete all the items in the list
		CustomListItem.deleteByList(data['_id'])

		# Delete the list and return the result
		return Services.Effect(
			oList.delete()
		)

	def list_update(self, data, sesh):
		"""List Update

		Updates the title on an existing list

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has at least csr messaging permission
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id', 'title'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the list
		oList = CustomList.get(data['_id'])
		if not oList:
			return Services.Effect(error=1104)

		# Make sure the agent owns the list
		if oList['agent'] != sesh['user_id']:
			return Services.Effect(error=1105)

		# Try to update the title
		try: oList['title'] = data['title']
		except ValueError as e: return Services.Effect(error=(1001, [e.args[0]]))

		# Update the record and return the result
		return Services.Effect(
			oList.save()
		)

	def listItem_create(self, data, sesh):
		"""List Item Create

		Adds a new item to an exiting or a new list

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has at least csr messaging permission
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['list', 'customer', 'name', 'number'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the list
		oList = CustomList.get(data['list'])
		if not oList:
			return Services.Effect(error=1104)

		# Make sure the agent owns the list
		if oList['agent'] != sesh['user_id']:
			return Services.Effect(error=1105)

		# Try to make an item instance
		try:
			oItem = CustomListItem(data)
		except ValueError as e:
			return Services.Effect(error=(1001, e.args[0]))

		# Create the item and return the ID
		try:
			return Services.Effect(oItem.create())

		# Data already in the given list, return error
		except Record_MySQL.DuplicateException:
			return Services.Effect(error=1101)

	def listItem_delete(self, data, sesh):
		"""List Item Delete

		Deletes a list item

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has at least csr messaging permission
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Effect(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the list item
		oListItem = CustomListItem.get(data['_id'])
		if not oListItem:
			return Services.Effect(error=(1104, 'item'))

		# Find the list associated
		oList = CustomList.get(oListItem['list'])
		if not oList:
			return Services.Effect(error=(1104, 'list'))

		# Make sure the agent owns the list
		if oList['agent'] != sesh['user_id']:
			return Services.Effect(error=1105)

		# Delete the list and return the result
		return Services.Effect(
			oListItem.delete()
		)

	def lists_read(self, data, sesh):
		"""Lists

		Returns all lists and their items belonging to the current agent

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""

		# Make sure the user has at least csr messaging permission
		oEff = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oEff.data:
			return Services.Effect(error=Rights.INVALID)

		# Find all lists associated with the user
		lLists = CustomList.filter({
			"agent": sesh['user_id']
		}, raw=['_id', 'title'])

		# If there's none
		if not lLists:
			return Services.Effect([])

		# Turn the list into a dictionary
		dLists = {
			d['_id']:{
				"_id": d['_id'],
				"title": d['title'],
				"items": []
			} for d in lLists
		}

		# Find all items associated with the lists
		lItems = CustomListItem.filter({
			"list": [d['_id'] for d in lLists]
		}, raw=True)

		# Go through each item and add it to the appropriate list
		for d in lItems:
			dLists[d['list']]['items'].append({
				"_id": d['_id'],
				"number": d['number'],
				"customer": d['customer'],
				"name": d['name']
			})

		# Return everything found sorted by title
		return Services.Effect(
			sorted(dLists.values(), key=lambda d: d['title'])
		)

	def templateEmail_create(self, data, sesh):
		"""Template Email Create

		Create a new email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._template_create(data, sesh, TemplateEmail)

	def templateEmail_delete(self, data, sesh):
		"""Template Email Delete

		Delete an existing email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._template_delete(data, sesh, TemplateEmail)

	def templateEmail_read(self, data, sesh):
		"""Template Email Read

		Fetches an existing email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._template_read(data, sesh, TemplateEmail)

	def templateEmail_update(self, data, sesh):
		"""Template Email Update

		Updated an existing email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._template_update(data, sesh, TemplateEmail)

	def templateEmails_read(self, data, sesh):
		"""Template Emails

		Fetches all existing email templates

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._templates_read(data, sesh, TemplateEmail)

	def templateSms_create(self, data, sesh):
		"""Template Sms Create

		Create a new sms template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._template_create(data, sesh, TemplateSMS)

	def templateSms_delete(self, data, sesh):
		"""Template Sms Delete

		Delete an existing sms template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._template_delete(data, sesh, TemplateSMS)

	def templateSms_read(self, data, sesh):
		"""Template Sms Read

		Fetches an existing sms template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._template_read(data, sesh, TemplateSMS)

	def templateSms_update(self, data, sesh):
		"""Template Sms Update

		Updated an existing sms template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._template_update(data, sesh, TemplateSMS)

	def templateSmss_read(self, data, sesh):
		"""Template SMSs

		Fetches all existing sms templates

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Effect
		"""
		return self._templates_read(data, sesh, TemplateSMS)
