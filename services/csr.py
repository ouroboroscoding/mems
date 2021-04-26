# coding=utf8
""" CSR Service

Handles all CSR requests
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-05-17"

# Python imports
import uuid

# Pip imports
from FormatOC import Node
from RestOC import DictHelper, Errors, JSON, Record_MySQL, Services, Sesh

# Shared imports
from shared import Rights

# Records imports
from records.csr import Agent, CustomList, CustomListItem, Reminder, \
						TemplateEmail, TemplateSMS, \
						Ticket, TicketAction, TicketItem

# Valid DOB
_DOB = Node('date')

class CSR(Services.Service):
	"""CSR Service class

	Service for CSR access
	"""

	_install = [Agent, CustomList, CustomListItem, TemplateEmail, TemplateSMS,
				Ticket, TicketAction, TicketItem]
	"""Record types called in install"""

	def _addTicketItems(ticket, items):
		"""Add Ticket Items

		Adds one or more items to an existing ticket

		Arguments:
			ticket (str): The ID of the ticket
			items (dict|list): The items to add

		Returns:
			list
		"""

		# If the ticket doesn't exist
		if not Ticket.exists(ticket):
			return Services.Error(1104)

		# If items is a dict
		if isinstance(items, dict):
			items = [items]

		# Init the return
		lRet = []

		# Go through each item
		for i in range(items):

			# Add the ticket ID
			items[i]['ticket'] = ticket

			# Create a new instance
			try:
				oItem = TicketItem(items[i])
			except ValueError as e:
				lRet.append(
					Services.Error(1001, [
						['%d.%s' % (i , l[0]), l[1]] for l in e.args[0]
					]))

			# Store the data and store the result
			lRet.append(
				oItem.create()
			)

		# Return the results
		return lRet

	def initialise(self):
		"""Initialise

		Initialises the instance and returns itself for chaining

		Returns:
			Monolith
		"""

		# Init the Ticket record class so that we get the action types
		TicketAction.init()

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
				"calendly": 1,				# Read
				"calendly_admin": 1,		# Read
				"csr_claims": 14,			# Update, Create, Delete
				"csr_messaging": 5,			# Read, Create
				"csr_templates": 1,			# Read
				"customers": 3,				# Read, Update
				"hubspot": 1,				# Read
				"justcall": 1,				# Read
				"memo_mips": 3,				# Read, Update
				"memo_notes": 5,			# Read, Create
				"orders": 7,				# Read, Update, Create
				"patient_account": 1,		# Read
				"prescriptions": 3,			# Read, Update
				"pharmacy_fill": 1,			# Read
				"welldyne_adhoc": 4			# Create
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
		for s in ['claims_max']:
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

	def agentMemo_create(self, data, sesh):
		"""Agent from Memo

		Creates an agent record from an existing Memo user instead of creating
		a new one

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
		try: DictHelper.eval(data, ['userName'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Look for the user
		oResponse = Services.read('monolith', 'user/id', {
			"_internal_": Services.internalKey(),
			"userName": data['userName']
		})
		if oResponse.errorExists() or oResponse.data is False:
			return oResponse

		# Create the agent and return the response
		return self._agent_create({
			"memo_id": oResponse.data,
			"claims_max": 20
		}, sesh)

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

		# If there's no agents
		if not lAgents:
			return Services.Response([])

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
				d['name'] = '%s %s' % (dMemoUsers[d['memo_id']]['firstName'], dMemoUsers[d['memo_id']]['lastName'])
				d['firstName'] = dMemoUsers[d['memo_id']]['firstName']
				d['lastName'] = dMemoUsers[d['memo_id']]['lastName']
				d['email'] = dMemoUsers[d['memo_id']]['email']
				d['dsClinicId'] = dMemoUsers[d['memo_id']]['dsClinicId']
				d['dsClinicianId'] = dMemoUsers[d['memo_id']]['dsClinicianId']
			else:
				d['userName'] = 'n/a'
				d['name'] = 'Not Found'
				d['firstName'] = 'Not'
				d['lastName'] = 'Found'
				d['email'] = ''
				d['dsClinicId'] = None
				d['dsClinicianId'] = None

		# Return the agents in order of userName
		return Services.Response(sorted(lAgents, key=lambda o: o['name']))

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

	def reminder_create(self, data, sesh):
		"""Reminder Create

		Creates a new reminder for the signed in agent

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If this is an internal request
		if '_internal_' in data:

			# Verify the key, remove it if it's ok
			if not Services.internalKey(data['_internal_']):
				return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
			del data['_internal_']

			# If the agent is missing
			if 'agent_id' not in data:
				return Services.Error(1001, [['agent_id', 'missing']])

			# Mark the creator as 0
			data['creator_id'] = 0

		# Else, this is a user
		else:

			# Make sure the user has at least csr messaging permission
			Rights.check(sesh, 'csr_messaging', Rights.READ)

			# Mark the agent and creator as the signed in user
			data['agent_id'] = sesh['memo_id']
			data['creator_id'] = sesh['memo_id']

		# Create an instance to test the fields
		try:
			oReminder = Reminder(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Create the reminder
		oReminder.create()

		# Store the raw record
		dReminder = oReminder.record()

		# If we have a crm type
		if 'crm_type' in dReminder and dReminder['crm_type']:

			# If it's knk
			if dReminder['crm_type'] == 'knk':

				# Fetch the claimed data
				oResponse = Services.read('monolith', 'internal/customersWithClaimed', {
					"_internal_": Services.internalKey(),
					"customerIds": [dReminder['crm_id']]
				}, sesh)

				# If we got data
				if oResponse.dataExists():

					# If we got the record
					if dReminder['crm_id'] in oResponse.data:

						# Store it in the reminder
						dReminder['claimed'] = oResponse.data[dReminder['crm_id']]

		# Return the raw record
		return Services.Response(dReminder)

	def reminder_delete(self, data, sesh):
		"""Reminder Delete

		Deletes an existing reminder for the signed in agent

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		Rights.check(sesh, 'csr_messaging', Rights.READ)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the reminder
		oReminder = Reminder.get(data['_id'])
		if not oReminder:
			return Services.Error(1104)

		# If the creator is not the signed in user
		if oReminder['creator_id'] != sesh['memo_id']:
			return Services.Error(1000)

		# Delete the reminder and return the result
		return Services.Response(
			oReminder.delete()
		)

	def reminder_update(self, data, sesh):
		"""Reminder Update

		Updates an existing reminder for the signed in agent

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		Rights.check(sesh, 'csr_messaging', Rights.READ)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the reminder
		oReminder = Reminder.get(data['_id'])
		if not oReminder:
			return Services.Error(1104)

		# If the creator is not the signed in user
		if oReminder['creator_id'] != sesh['memo_id']:
			return Services.Error(1000)

		# If the reminder is already resolved
		if oReminder['resolved']:
			return Services.Error(1002)

		# Remove fields that can't be changed
		del data['_id']
		if '_created' in data: del data['_created']
		if 'agent_id' in data: del data['agent_id']
		if 'creator_id' in data: del data['creator_id']
		if 'resolved' in data == False: del data['resolved']

		# Update all reminaing fields and keep track of any errors
		lErrors = []
		for f in data:
			try: oReminder[f] = data[f]
			except ValueError as e: lErrors.extend(e.args[0])

		# If there's any errors
		if lErrors:
			return Services.Error(1001, lErrors)

		# Save the record and return the result
		return Services.Response(
			oReminder.save()
		)

	def reminderResolve_update(self, data, sesh):
		"""Reminder Create

		Marks the reminder as resolved for the signed in patient

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		Rights.check(sesh, 'csr_messaging', Rights.READ)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [['_id', 'missing']])

		# Find the reminder
		oReminder = Reminder.get(data['_id'])
		if not oReminder:
			return Services.Error(1104)

		# If the creator is not the signed in user
		if oReminder['creator_id'] != sesh['memo_id']:
			return Services.Error(1000)

		# If the reminder is already resolved
		if oReminder['resolved']:
			return Services.Response(True)

		# Mark the reminder as resolved and return the result
		oReminder['resolved'] = True
		return Services.Response(
			oReminder.save()
		)

	def reminders_read(self, data, sesh):
		"""Reminders

		Returns the unresolved reminders for the agent

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		Rights.check(sesh, 'csr_messaging', Rights.READ)

		# Fetch all reminders not resolved for the signed in agent
		lReminders = Reminder.filter({
			"agent_id": sesh['memo_id'],
			"resolved": False
		}, raw=True, orderby='date')

		# CRM IDs
		dCrmIds = {"knk": []}
		dClaimed ={"knk": {}}

		# Go through each one and store the ID by CRM
		for d in lReminders:

			# If we have a crm type
			if 'crm_type' in d and d['crm_type']:

				# Store the id by type
				dCrmIds[d['crm_type']].append(d['crm_id'])

		# If we have any KNK ones
		if dCrmIds['knk']:

			# Fetch the claimed data
			oResponse = Services.read('monolith', 'internal/customersWithClaimed', {
				"_internal_": Services.internalKey(),
				"customerIds": dCrmIds['knk']
			}, sesh)

			# If we got an error
			if oResponse.errorExists():
				return oResponse

			# If we got data, store it
			if oResponse.dataExists():
				dClaimed['knk'] = oResponse.data

		# Go through each reminder
		for d in lReminders:

			# Init claimed
			d['claimed'] = None

			# If we have a crm_type
			if 'crm_type' in d and d['crm_type']:

				# If we have claimed
				if d['crm_id'] in dClaimed[d['crm_type']]:
					d['claimed'] = dClaimed[d['crm_type']][d['crm_id']]

		# Return the reminders
		return Services.Response(lReminders)

	def remindersCount_read(self, data, sesh):
		"""Reminders Count

		Returns the number of unresolved reminders for the given data and
		previous days, for the signed in agent

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has at least csr messaging permission
		Rights.check(sesh, 'csr_messaging', Rights.READ)

		# If the data is missing
		if 'date' not in data:
			return Services.Error(1001, [['date', 'missing']])

		# Fetch the count of unresolved reminders and return it
		return Services.Response(
			Reminder.count(filter={
				"agent_id": sesh['memo_id'],
				"date": {"lte": data['date']},
				"resolved": False
			})
		)

	def session_read(self, data, sesh):
		"""Session

		Returns the ID of the user logged into the current session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If the session doesn't start with "csr:" it's not valid
		if sesh.id()[0:4] != 'csr:':
			return Services.Response(error=102)

		# Return the session info
		return Services.Response({
			"memo": {"id": sesh['memo_id']},
			"user" : {"id": sesh['user_id']}
		})

	def signin_create(self, data):
		"""Signin

		Signs a user into the system

		Arguments:
			data (dict): The data passed to the request

		Returns:
			Result
		"""

		# Verify fields
		try: DictHelper.eval(data, ['userName', 'passwd'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Check monolith for the user
		data['_internal_'] = Services.internalKey()
		oResponse = Services.create('monolith', 'signin', data)
		if oResponse.errorExists(): return oResponse

		# Create a new session
		oSesh = Sesh.create("csr:" + uuid.uuid4().hex)

		# Store the user ID and information in it
		oSesh['memo_id'] = oResponse.data['id']

		# Save the session
		oSesh.save()

		# Check for the agent associated with the memo ID
		dAgent = Agent.filter(
			{"memo_id": oResponse.data['id']},
			raw=True,
			limit=1
		)

		# If there's no such user
		if not dAgent:
			return Services.Response(error=Rights.INVALID)

		# Store the user ID and claim vars in the session
		oSesh['user_id'] = dAgent['_id']
		oSesh['claims_max'] = dAgent['claims_max']
		oSesh.save()

		# Return the session ID and primary user data
		return Services.Response({
			"memo": {"id": oSesh['memo_id']},
			"session": oSesh.id(),
			"user": {"id": dAgent['_id']}
		})

	def signout_create(self, data, sesh):
		"""Signout

		Called to sign out a user and destroy their session

		Arguments:
			data (dict): Data sent with the request
			sesh (Sesh._Session): The session associated with the user

		Returns:
			Services.Response
		"""

		# Close the session so it can no longer be found/used
		sesh.close()

		# Return OK
		return Services.Response(True)

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

	def ticket_create(self, data, sesh):
		"""Ticket Create

		Creates a new ticket

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check internal key or rights
		Rights.internalOrCheck(data, sesh, 'csr_claims', Rights.CREATE)

		# If the crm data is missing
		if 'crm_type' not in data:

			# If the phone number is missing
			if 'phone_number' not in data:
				return Services.Error(1001, [('phone_number', 'missing')])

			# Assume konnektive
			data['crm_type'] = 'knk'

			# Fetch the ID from monolith
			oResponse = Services.read('monolith', 'customer/id/byPhone', {
				"phoneNumber": data['phone_number'][-10:]
			})
			if oResponse.errorExists():
				return oResponse

			# Store the ID
			data['crm_id'] = str(oResponse.data['customerId'])

		# If we got any actions
		try: dAction = data.pop('action')
		except KeyError: dAction = False

		# If we got any items
		try: lItems = data.pop('items')
		except KeyError: lItems = False

		# Create an instance to test the fields
		try:
			oTicket = Ticket(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Store the ticket
		sID = oTicket.create()

		# If we have an action
		if dAction:

			# Verify minimum fields
			try: DictHelper.eval(dAction, ['type', 'subtype'])
			except ValueError as e: return Services.Error(1001, [('action.%s' % f, 'missing') for f in e.args])

			# Make sure the type is valid
			if dAction['type'] not in self._ticket_action_types:
				return Services.Error(1001, [('action.type', 'invalid')])

			# Make sure the subtype is valid
			if dAction['subtype'] not in self._ticket_action_subtypes[dAction['type']]:
				return Services.Error(1001, [('action.subtype', 'invalid')])

			# Add the ticket ID to the action
			dAction['ticket'] = sID

			# Add the memo ID from the session
			dAction['memo_id'] = sesh['memo_id']

			# Create a new instance
			try:
				oAction = TicketAction(dAction)
			except ValueError as e:
				return Services.Error(1001, ['action.%s' % l[0] for l in e.args[0]])

			# Store the data
			oAction.create()

		# Init warning
		mWarning = []

		# If we have items
		if lItems:

			# Add the items
			lRes = self._addTicketItems(sID, lItems)

			# Go through the results, if any are errors, add them to the warning
			for o in lRes:
				if o.errorExists():
					mWarning.append(str(o))

		# Return the ID of the new ticket
		return Services.Response(sID, warning=(mWarning and ('Failed Items: %s' % str([str(o) for o in mWarning])) or None))

	def ticketAction_create(self, data, sesh):
		"""Ticket Action Create

		Adds a new action to an existing ticket

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check internal key or rights
		Rights.internalOrCheck(data, sesh, 'csr_claims', Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['ticket', 'type', 'subtype'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If the ticket doesn't exist
		if not Ticket.exists(data['ticket']):
			return Services.Error(1104)

		# Make sure the type is valid
		if data['type'] not in self._ticket_action_types:
			return Services.Error(1001, [('type', 'invalid')])

		# Make sure the subtype is valid
		if data['subtype'] not in self._ticket_action_subtypes[data['type']]:
			return Services.Error(1001, [('subtype', 'invalid')])

		# Add the memo ID from the session
		data['memo_id'] = sesh['memo_id']

		# Create a new instance
		try:
			oAction = TicketAction(oAction)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Store the data and return the result
		return Services.Response(
			oAction.create()
		)

	def ticketExists_read(self, data, sesh):
		"""Ticket Exists Read

		Returns if the given phone number or customer ID already has a ticket
		associated or not

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check internal key or rights
		Rights.internalOrCheck(data, sesh, 'csr_claims', Rights.READ)

		# Init the filter
		dFilter = {}

		# If we have a CRM type and ID
		if 'crm_type' in data and 'crm_id' in data:
			dFilter['crm_type'] = data['crm_type']
			dFilter['crm_id'] = data['crm_id']

		# Else, if we have a phone number
		elif 'phone_number' in data:
			dFilter['phone_number'] = data['phone_number']

		# Else, invalid data
		else:
			return Services.Error(1001, [('crm_type', 'missing'), ('crm_id', 'missing')])

		# Check if resolved is null
		dFilter['resolved'] = None

		# Find the ticket
		dTicket = Ticket.filter(dFilter, raw=['_id'])

		# Return the ID or false
		return Services.Response(
			dTicket and dTicket['_id'] or False
		)

	def ticketItems_create(self, data, sesh):
		"""Ticket Items Create

		Adds a one or more items to an existing ticket

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check internal key or rights
		Rights.internalOrCheck(data, sesh, 'csr_claims', Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['ticket', 'items'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Add the items and return the result
		return Services.Response(
			self._addTicketItems(data['ticket'], data['items'])
		)

	def ticketsCustomer_read(self, data, sesh):
		"""Tickets by Customer

		Returns all the tickets associated with a specific customer

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check rights
		Rights.check(data, sesh, 'csr_claims', Rights.READ)

		# If we have crm type and ID
		if 'crm_type' in data and 'crm_id' in data:

			# Find all the records by ID
			lTickets = Ticket.filter({
				"crm_type": data['crm_type'],
				"crm_id": data['crm_id']
			}, raw=True, orderby='_created')

		# Else, if we got a phone number
		elif 'phone_number' in data:

			# Find all the records by phone number
			lTickets = Ticket.filter({
				"phone_number": data['phone_number']
			}, raw=True, orderby='_created')

		# Else, missing data
		else:
			return Services.Error(1001, [('crm_type', 'missing'), ('crm_id', 'missing')])

		# Return the tickets
		return Services.Response(lTickets)

	def ticketsUser_read(self, data, sesh):
		"""Tickets by User

		Returns all the tickets a user has any action on

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If the user is not the one signed in
		if ('user' in data and data['user'] != sesh['user_id']) or \
			('memo_id' in data and data['memo_id'] != sesh['memo_id']):

			# Check rights
			Rights.check(data, sesh, 'csr_overwrite', Rights.READ)

		# If the memo_id is missing
		if 'memo_id' not in data:
			return Services.Error(1001, [('memo_id', 'missing')])

		# Init the filter data
		dFilter = {"memo_id": data['memo_id']}

		# If we got a range
		if 'range' in data:
			dFilter['_created'] = {"between": [
				data['range']['start'],
				data['range']['end']
			]}

		# Get a list of the actions and ticket IDS the user is associated with
		lActions = Actions.filter(dFilter, raw=['ticket', 'type'])

		# Go through all the actions found and generate a list of unique tickets
		#	and their actions
		dTicketActions = {}
		for d in lActions:
			try: dTicketActions[d['ticket']].append(d['type'])
			except KeyError: dTicketActions[d['ticket']] =[d['type']]

		# Fetch the tickets by IDs in order by created
		lTickets = Ticket.withResolution(
			list(dTicketActions.keys())
		)

		# Go through each ticket and add the associated actions for the user
		for d in lTickets:
			d['actions'] = d['_id'] in dTicketActions and \
							dTicketActions[d['_id']] or \
							'N/A'

		# Return the tickets
		return Services.Response(lTickets)
