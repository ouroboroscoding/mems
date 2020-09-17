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
from FormatOC import Node
from RestOC import DictHelper, Errors, Record_MySQL, Services

# Shared imports
from shared import Rights

# Records imports
from records.csr import Agent, CustomList, CustomListItem, TemplateEmail, \
						TemplateSMS

# Valid DOB
_DOB = Node('date')

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

	def _agent_create(self, data, sesh):
		"""Agent Create

		Creates the actual agent record in the DB as well as necessary
		permissions

		Arguments:
			data (dict): The ID of the user in Memo as well as claim vars
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Create a new agent instance using the memo ID
		try:
			oAgent = Agent(data)
		except ValueError:
			return Services.Response(error=(1001, e.args[0]))

		# Create the agent and store the ID
		try:
			sID = oAgent.create()
		except Record_MySQL.DuplicateException as e:
			return Services.Response(error=1101)

		# Create the default permissions
		oResponse = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": sID,
			"permissions": {
				"calendly": 1,
				"csr_claims": 14,
				"csr_messaging": 5,
				"csr_templates": 1,
				"customers": 1,
				"memo_mips": 3,
				"memo_notes": 5,
				"patient_account": 1,
				"prescriptions": 3,
				"pharmacy_fill": 1,
				"welldyne_adhoc": 4
			}
		}, sesh)
		if oResponse.errorExists():
			print(oResponse)
			return Services.Response(sID, warning='Failed to creater permissions for agent')

		# Create the agent and return the ID
		return Services.Response(sID)

	def _template_create(self, data, sesh, _class):
		"""Template Create

		Create a new template of the passed type

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			_class (class): The class to use

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['title', 'content'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Validate by creating a Record instance
		try:
			oTemplate = _class(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the row and return the result
		return Services.Response(
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
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.DELETE,
			"ident": data['_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# If the record does not exist
		if not _class.exists(data['_id']):
			return Services.Response(error=1104)

		# Delete the record
		if not _class.deleteGet(data['_id']):
			return Services.Response(error=1102)

		# Return OK
		return Services.Response(True)

	def _template_read(self, data, sesh, _class):
		"""Template Read

		Fetches an existing template of the passed type

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			_class (class): The class to use

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.READ,
			"ident": data['_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Look for the template
		dTemplate = _class.get(data['_id'], raw=True)

		# If it doesn't exist
		if not dTemplate:
			return Services.Response(error=1104)

		# Return the template
		return Services.Response(dTemplate)

	def _template_update(self, data, sesh, _class):
		"""Template Update

		Updated an existing template of the passed type

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request
			_class (class): The class to use

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.UPDATE,
			"ident": data['_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch the template
		oTemplate = _class.get(data['_id'])

		# If it doesn't exist
		if not oTemplate:
			return Services.Response(error=1104)

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
			return Services.Response(error=(1001, lErrors))

		# Update the record and return the result
		return Services.Response(
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
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_templates",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch and return the templates
		return Services.Response(
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
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.CREATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['userName', 'firstName', 'lastName', 'password'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Pull out CSR only values
		dAgent = {}
		if 'claims_max' in data: dAgent['claims_max'] = data.pop('claims_max')
		if 'claims_timeout' in data: dAgent['claims_timeout'] = data.pop('claims_timeout')

		# Send the data to monolith to create the memo user
		data['_internal_'] = Services.internalKey()
		oResponse = Services.create('monolith', 'user', data, sesh)
		if oResponse.errorExists(): return oResponse

		# Add the memo ID
		dAgent['memo_id'] = oResponse.data

		# Create the agent record
		return self._agent_create(dAgent, sesh)

	def agent_delete(self, data, sesh):
		"""Agent Delete

		Deletes an existing memo user record associated

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.DELETE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Find the Agent
		oAgent = Agent.get(data['_id'])

		# Use the memo ID to mark the memo user as inactive
		oResponse = Services.update('monolith', 'user/active', {
			"_internal_": Services.internalKey(),
			"id": oAgent['memo_id'],
			"active": False
		}, sesh)
		if oResponse.errorExists(): return oResponse

		# Delete all permissions
		oResponse = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": data['_id'],
			"permissions": {}
		}, sesh);
		if oResponse.errorExists(): return oResponse

		# Delete the record and return the result
		return Services.Response(
			oAgent.delete()
		)

	def agent_read(self, data, sesh):
		"""Agent Read

		Fetches one, many, or all user records

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		pass

	def agent_update(self, data, sesh):
		"""Agent Update

		Updates an existing agent (via memo user)

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.UPDATE
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Find the agent
		oAgent = Agent.get(data['_id'])
		if not oAgent:
			return Services.Response(error=1104)

		# Try to update the claims vars
		lErrors = []
		for s in ['claims_max', 'claims_timeout']:
			if s in data:
				try: oAgent[s] = data.pop(s)
				except ValueError as e: lErrors.append(e.args[0])
		if lErrors:
			return Services.Response(error=(1001, lErrors))

		# If there's any changes
		if oAgent.changes():
			oAgent.save()

		# Remove the agent ID
		del data['_id']

		# If there's still stuff to change
		if data:

			# Add the memo ID
			data['id'] = oAgent['memo_id']

			# Pass the info on to monolith service
			data['_internal_'] = Services.internalKey()
			oResponse = Services.update('monolith', 'user', data, sesh)

			# Return whatever monolith returned
			return oResponse

		# Else, return OK
		else:
			return Services.Response(True)

	def agentInternal_read(self, data, sesh):
		"""Agent Internal

		Fetches a memo user by their Memo ID rather then their primary key.
		Internal function, can not be used from outside

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['_internal_', 'id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Look up the record
		dAgent = Agent.filter(
			{"memo_id": data['id']},
			raw=True,
			limit=1
		)

		# If there's no such user
		if not dAgent:
			return Services.Response(error=1104)

		# Return the user
		return Services.Response(dAgent)

	def agentPasswd_update(self, data, sesh):
		"""Agent Password Update

		Updates an agent's password in monolith

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['agent_id', 'passwd'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.UPDATE,
			"ident": data['agent_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Find the Agent
		dAgent = Agent.get(data['agent_id'], raw=['memo_id'])
		if not dAgent:
			return Services.Response(error=1104)

		# Send the data to monolith to update the password
		oResponse = Services.update('monolith', 'user/passwd', {
			"_internal_": Services.internalKey(),
			"user_id": dAgent['memo_id'],
			"passwd": data['passwd']
		}, sesh)

		# Return the result, regardless of what it is
		return oResponse

	def agentPermissions_read(self, data, sesh):
		"""Agent Permissions Read

		Returns all permissions associated with an agent

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['agent_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.READ,
			"ident": data['agent_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch the permissions from the auth service
		oResponse = Services.read('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": data['agent_id']
		}, sesh)

		# Return whatever was found
		return oResponse

	def agentPermissions_update(self, data, sesh):
		"""Agent Permissions Update

		Updates the permissions associated with an agent

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['agent_id', 'permissions'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.READ,
			"ident": data['agent_id']
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch the permissions from the auth service
		oResponse = Services.update('auth', 'permissions', {
			"_internal_": Services.internalKey(),
			"user": data['agent_id'],
			"permissions": data['permissions']
		}, sesh)

		# Return whatever was found
		return oResponse

	def agentNames_read(self, data, sesh):
		"""Agent Names

		Returns the list of agents who can have issues transfered / escalated to
		them

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Fetch all the agents
		lAgents = Agent.get(raw=['memo_id'])

		# Fetch their names
		oResponse = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": [d['memo_id'] for d in lAgents]
		}, sesh)

		# Regardless of what we got, retun the effect
		return oResponse

	def agents_read(self, data, sesh):
		"""Agents

		Returns all agents in the system

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_agents",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Fetch all the agents
		lAgents = Agent.get(raw=True)

		# Fetch all the Memo user's associated
		oResponse = Services.read('monolith', 'users', {
			"_internal_": Services.internalKey(),
			"id": [d['memo_id'] for d in lAgents],
			"fields": ['id', 'userName', 'firstName', 'lastName', 'email', 'dsClinicId', 'dsClinicianId']
		}, sesh)
		if oResponse.errorExists(): return oResponse

		# Turn it into a dictionary
		dMemoUsers = {d['id']:d for d in oResponse.data}

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
		return Services.Response(sorted(lAgents, key=lambda o: o['userName']))

	def list_create(self, data, sesh):
		"""List Create

		Create a new custom list

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['title'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Try to make an instance
		try:
			oList = CustomList({
				"agent": sesh['user_id'],
				"title": data['title']
			})
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the row and return the result
		return Services.Response(
			oList.create()
		)

	def list_delete(self, data, sesh):
		"""List Delete

		Deletes a list and all items

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the list
		oList = CustomList.get(data['_id'])
		if not oList:
			return Services.Response(error=1104)

		# Make sure the agent owns the list
		if oList['agent'] != sesh['user_id']:
			return Services.Response(error=1105)

		# Delete all the items in the list
		CustomListItem.deleteByList(data['_id'])

		# Delete the list and return the result
		return Services.Response(
			oList.delete()
		)

	def list_update(self, data, sesh):
		"""List Update

		Updates the title on an existing list

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id', 'title'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the list
		oList = CustomList.get(data['_id'])
		if not oList:
			return Services.Response(error=1104)

		# Make sure the agent owns the list
		if oList['agent'] != sesh['user_id']:
			return Services.Response(error=1105)

		# Try to update the title
		try: oList['title'] = data['title']
		except ValueError as e: return Services.Response(error=(1001, [e.args[0]]))

		# Update the record and return the result
		return Services.Response(
			oList.save()
		)

	def listItem_create(self, data, sesh):
		"""List Item Create

		Adds a new item to an exiting or a new list

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['list', 'customer', 'name', 'number'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the list
		oList = CustomList.get(data['list'])
		if not oList:
			return Services.Response(error=1104)

		# Make sure the agent owns the list
		if oList['agent'] != sesh['user_id']:
			return Services.Response(error=1105)

		# Try to make an item instance
		try:
			oItem = CustomListItem(data)
		except ValueError as e:
			return Services.Response(error=(1001, e.args[0]))

		# Create the item and return the ID
		try:
			return Services.Response(oItem.create())

		# Data already in the given list, return error
		except Record_MySQL.DuplicateException:
			return Services.Response(error=1101)

	def listItem_delete(self, data, sesh):
		"""List Item Delete

		Deletes a list item

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the list item
		oListItem = CustomListItem.get(data['_id'])
		if not oListItem:
			return Services.Response(error=(1104, 'item'))

		# Find the list associated
		oList = CustomList.get(oListItem['list'])
		if not oList:
			return Services.Response(error=(1104, 'list'))

		# Make sure the agent owns the list
		if oList['agent'] != sesh['user_id']:
			return Services.Response(error=1105)

		# Delete the list and return the result
		return Services.Response(
			oListItem.delete()
		)

	def lists_read(self, data, sesh):
		"""Lists

		Returns all lists and their items belonging to the current agent

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		oResponse = Services.read('auth', 'rights/verify', {
			"name": "csr_messaging",
			"right": Rights.READ
		}, sesh)
		if not oResponse.data:
			return Services.Response(error=Rights.INVALID)

		# Find all lists associated with the user
		lLists = CustomList.filter({
			"agent": sesh['user_id']
		}, raw=['_id', 'title'])

		# If there's none
		if not lLists:
			return Services.Response([])

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
		return Services.Response(
			sorted(dLists.values(), key=lambda d: d['title'])
		)

	def patientAccount_create(self, data, sesh):
		"""Patient Account Create

		Gets the necessary data to create a patient account and sends it off
		to the patient service

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['crm_type', 'crm_id'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If the type is KNK
		if data['crm_type'] == 'knk':

			# Try to get the DOB from monolith
			oResponse = Services.read('monolith', 'customer/dob', {
				"customerId": str(data['crm_id'])
			}, sesh)
			if oResponse.errorExists(): return oResponse

			# If the DOB isn't valid
			if not _DOB.valid(oResponse.data):
				return Services.Response(error=1910)

			# Add the DOB to the data
			data['dob'] = oResponse.data

		# Else, invalid crm type
		else:
			return Services.Response(error=1003)

		# Pass along the details to the patient service and return the result
		return  Services.create('patient', 'setup/start', data, sesh)

	def templateEmail_create(self, data, sesh):
		"""Template Email Create

		Create a new email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._template_create(data, sesh, TemplateEmail)

	def templateEmail_delete(self, data, sesh):
		"""Template Email Delete

		Delete an existing email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._template_delete(data, sesh, TemplateEmail)

	def templateEmail_read(self, data, sesh):
		"""Template Email Read

		Fetches an existing email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._template_read(data, sesh, TemplateEmail)

	def templateEmail_update(self, data, sesh):
		"""Template Email Update

		Updated an existing email template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._template_update(data, sesh, TemplateEmail)

	def templateEmails_read(self, data, sesh):
		"""Template Emails

		Fetches all existing email templates

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._templates_read(data, sesh, TemplateEmail)

	def templateSms_create(self, data, sesh):
		"""Template Sms Create

		Create a new sms template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._template_create(data, sesh, TemplateSMS)

	def templateSms_delete(self, data, sesh):
		"""Template Sms Delete

		Delete an existing sms template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._template_delete(data, sesh, TemplateSMS)

	def templateSms_read(self, data, sesh):
		"""Template Sms Read

		Fetches an existing sms template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._template_read(data, sesh, TemplateSMS)

	def templateSms_update(self, data, sesh):
		"""Template Sms Update

		Updated an existing sms template

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._template_update(data, sesh, TemplateSMS)

	def templateSmss_read(self, data, sesh):
		"""Template SMSs

		Fetches all existing sms templates

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""
		return self._templates_read(data, sesh, TemplateSMS)
