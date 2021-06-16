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
from operator import itemgetter
from time import time
import uuid

# Pip imports
import arrow
from FormatOC import Node
from RestOC import DictHelper, Errors, JSON, Record_MySQL, Services, Sesh

# Shared imports
from shared import Rights

# Records imports
from records.csr import Agent, AgentOfficeHours, CustomList, CustomListItem, \
						Reminder, TemplateEmail, TemplateSMS, \
						Ticket, TicketAction, TicketItem, \
						TicketOpened, TicketResolved, TicketStat

# Valid DOB
_DOB = Node('date')

# Placeholder UUID
UUID_PLACEHOLDER = 'aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa'

# Python DOW to Office Hours DOW
DAY_OF_WEEK = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

class CSR(Services.Service):
	"""CSR Service class

	Service for CSR access
	"""

	_install = [Agent, AgentOfficeHours, CustomList, CustomListItem, TemplateEmail,
				TemplateSMS, Ticket, TicketAction, TicketItem, TicketOpened,
				TicketResolved, TicketStat]
	"""Record types called in install"""

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

	@classmethod
	def _calculateReturnToOffice(cls, dt, time, dow, hours):
		"""Calculate Return To Office

		Calculates the time before an agent is back online based on their
		working office hours

		Arguments:
			dt (Arrow): The current date/time as an Arrow instance
			time (str): The current time in HH:mm:ss,
			dow (str): The 3 letter day of the week, e.g. mon, wed, sat
			hours (dict): The current hours by day of the week for the agent

		Returns:
			str
		"""

		# If the agent has no office hours
		if not hours:
			return 'never'

		# If we have today and it's before
		elif dow in hours and \
			time < hours[dow]['start']:

			# Get the time they start
			lTime = hours[dow]['start'].split(':')
			oStart = dt.replace(hour=int(lTime[0], 10), minute=int(lTime[1], 10), second=0, microsecond=0)

		# Else, it's on another day
		else:

			print('hours: %s' % str(hours))

			# Get the current weekday and add 1
			iCurrent = dt.weekday()

			print('iCurrent: %d' % iCurrent)

			# Go through each day until I find one with hours
			iNext = 0
			for i in range(7):

				# Calculate the day to check
				iNext = (i + (iCurrent < 6 and (iCurrent + 1) or 0)) % 7

				# If we have hours
				if DAY_OF_WEEK[iNext] in hours:
					break

			print('iNext: %d' % iNext)

			# Figure out the days to add
			iDaysToAdd = iNext > iCurrent and iNext - iCurrent or (7 + (iNext - iCurrent))

			print('iDaysToAdd: %d' % iDaysToAdd)

			# Get the time they start
			lTime = hours[DAY_OF_WEEK[iNext]]['start'].split(':')
			oStart = dt.shift(days=iDaysToAdd).replace(hour=int(lTime[0], 10), minute=int(lTime[1], 10), second=0, microsecond=0)

		# Calculate the difference between when they start and now
		oDiff = oStart - dt

		# Calculate hours and minutes
		iHours, iRemainder = divmod(oDiff.seconds, 3600)
		iMinutes, iSeconds = divmod(iRemainder, 60)

		# Init the string diff
		lDiff = []

		# If we have days
		if oDiff.days:
			lDiff.append('%d %s' % (oDiff.days, oDiff.days > 1 and 'days' or 'day'))

		# If we have hours
		if iHours:
			lDiff.append('%d %s' % (iHours, iHours > 1 and 'hours' or 'hour'))

		# If we have minutes
		if iMinutes:
			lDiff.append('%d %s' % (iMinutes, iMinutes > 1 and 'minutes' or 'minute'))

		# If by some fluke it's right now
		if not lDiff:
			return 'right now'

		# Join the parts and return
		return 'in %s' % ', '.join(lDiff)

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
		Rights.check(sesh, 'csr_templates', Rights.CREATE)

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
		Rights.check(sesh, 'csr_templates', Rights.DELETE, data['_id'])

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
		Rights.check(sesh, 'csr_templates', Rights.READ, data['_id'])

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
		Rights.check(sesh, 'csr_templates', Rights.UPDATE, data['_id'])

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
		Rights.check(sesh, 'csr_templates', Rights.READ)

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
		Rights.check(sesh, 'csr_agents', Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['userName', 'firstName', 'lastName', 'password'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Pull out CSR only values
		dAgent = {}
		for k in ['type', 'escalate', 'label', 'claims_max']:
			if k in data: dAgent[k] = data.pop(k)

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
		Rights.check(sesh, 'csr_agents', Rights.DELETE)

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
		Rights.check(sesh, 'csr_agents', Rights.UPDATE)

		# Find the agent
		oAgent = Agent.get(data['_id'])
		if not oAgent:
			return Services.Response(error=1104)

		# Try to update the claims vars
		lErrors = []
		for s in ['type', 'escalate', 'label', 'claims_max', 'oof', 'oof_replacement']:
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

	def agentHours_read(self, data, sesh):
		"""Agent Hours read

		Fetches the list of days and hours the agent works

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'csr_agents', Rights.READ)

		# Make sure we have the memo_id
		if 'memo_id' not in data:
			return Services.Error(1001, [('memo_id', 'missing')])

		# Fetch and return the records found for the memo user
		return Services.Response(
			AgentOfficeHours.filter({
				"memo_id": data['memo_id']
			}, raw=['dow', 'start', 'end'])
		)

	def agentHours_update(self, data, sesh):
		"""Agent Hours update

		Overwrites the hours the agent works

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Make sure the user has the proper permission to do this
		Rights.check(sesh, 'csr_agents', Rights.UPDATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['memo_id', 'hours'])
		except ValueError as e: return Services.Error(1001, [(f, 'missing') for f in e.args])

		# If hours is not a list
		if not isinstance(data['hours'], list):
			return Services.Error(1001, [('hours', 'not a list')])

		# Go through each item and make sure all data is there
		lHours = []
		for i in range(len(data['hours'])):
			try:
				data['hours'][i]['memo_id'] = data['memo_id']
				lHours.append(AgentOfficeHours(data['hours'][i]))
			except ValueError as e:
				return Services.Error(1001, [('hours.%d.%s' % (i, l[0]), l[1]) for l in e.args[0]])

		# Delete any existing hours for the user
		AgentOfficeHours.deleteGet(data['memo_id'], index='memo_id')

		# Add the new ones
		AgentOfficeHours.createMany(lHours)

		# Return OK
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
		Rights.check(sesh, 'csr_agents', Rights.CREATE)

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
			"type": 'agent',
			"escalate": 0,
			"label": '',
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

		# Get the current date/time in EST
		oDT = arrow.get().to('US/Eastern');

		# Get the current time as a string
		sTime = oDT.format('HH:mm:ss')

		# Get the day of the week as a string
		sDOW = DAY_OF_WEEK[oDT.weekday()]

		# Fetch all the agents
		lAgents = Agent.get(raw=['memo_id', 'type', 'escalate', 'label', 'oof', 'oof_replacement'])

		# Fetch all office hours and store them by agent
		dOfficeHours = {}
		for d in AgentOfficeHours.get(raw=True):
			try: dOfficeHours[d['memo_id']][d['dow']] = {"start": d['start'],"end": d['end']}
			except KeyError: dOfficeHours[d['memo_id']] = {d['dow']:{"start": d['start'],"end": d['end']}}

		# Fetch their names
		oResponse = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": [d['memo_id'] for d in lAgents]
		}, sesh)

		# Convert the IDs
		dMemoNames = DictHelper.keysToInts(oResponse.data)

		# Go through each agent
		for d in lAgents:

			# Are they offline?
			if d['memo_id'] not in dOfficeHours or \
				sDOW not in dOfficeHours[d['memo_id']] or \
				sTime < dOfficeHours[d['memo_id']][sDOW]['start'] or \
				sTime > dOfficeHours[d['memo_id']][sDOW]['end']:

				# Calculate the time before the agent returns
				d['offline'] = self._calculateReturnToOffice(
					oDT,
					sTime,
					sDOW,
					dOfficeHours[d['memo_id']]
				)

			# Try to find the name for the agent
			try: dName = dMemoNames[d['memo_id']]
			except KeyError: dName = {"firstName": 'NAME', "lastName": 'MISSING'}
			d['firstName'] = dName['firstName']
			d['lastName'] = dName['lastName']

			# If we have a replacement, look for that name as well
			if d['oof'] and d['oof_replacement']:
				try: dName = dMemoNames[d['oof_replacement']]
				except KeyError: dName = {"firstName": 'NAME', "lastName": 'MISSING'}
				d['oof_replacement_firstName'] = dName['firstName']
				d['oof_replacement_lastName'] = dName['lastName']

		# Order by first then last name
		lAgents = sorted(lAgents, key=itemgetter('firstName', 'lastName'))

		# Return the agents
		return Services.Response(lAgents)

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
		Rights.check(sesh, 'csr_agents', Rights.UPDATE, data['agent_id'])

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
		Rights.check(sesh, 'csr_agents', Rights.READ, data['agent_id'])

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
		Rights.check(sesh, 'csr_agents', Rights.UPDATE, data['agent_id'])

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
		Rights.check(sesh, 'csr_agents', Rights.READ)

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
				d['name'] = 'NAME MISSING'
				d['firstName'] = 'NAME'
				d['lastName'] = 'MISSING'
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
		Rights.check(sesh, 'csr_messaging', Rights.READ)

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
		Rights.check(sesh, 'csr_messaging', Rights.READ)

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
		Rights.check(sesh, 'csr_messaging', Rights.READ)

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
		Rights.check(sesh, 'csr_messaging', Rights.READ)

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
		Rights.check(sesh, 'csr_messaging', Rights.READ)

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
		Rights.check(sesh, 'csr_messaging', Rights.READ)

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
		Rights.internalOrCheck(data, sesh, ['csr_claims', 'order_claims'], Rights.CREATE)

		# Create a new opened instance
		try:
			oOpened = TicketOpened({
				"_ticket": UUID_PLACEHOLDER,
				"type": data['type'],
				"memo_id": sesh['memo_id']
			})

			# Remove the type from the data so it doesn't trip up the Ticket
			#	create
			data.pop('type')

		except ValueError as e:
			return Services.Error(1001, ['action.%s' % l[0] for l in e.args[0]])

		# Try to pop off the items
		try: lItemsData = data.pop('items')
		except KeyError: lItemsData = False

		# Create a list of items records
		lItems = []

		# If the pop worked
		if lItemsData:

			# Go through each item
			for i in range(len(lItemsData)):

				# Add ticket ID to the item
				lItemsData[i]['ticket'] = UUID_PLACEHOLDER

				# Make sure the identifier is a string
				if 'identifier' in lItemsData[i]:
					lItemsData[i]['identifier'] = str(lItemsData[i]['identifier'])

				# Create a new instance
				try:
					oItem = TicketItem(lItemsData[i])
				except ValueError as e:
					return Services.Error(1001, ['item.%d.%s' % (i, l[0]) for l in e.args[0]])

			# Add it to the list
			lItems.append(oItem)

		# Create an instance to test the fields
		try:
			oTicket = Ticket(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Create the ticket and store the ID
		sID = oTicket.create()

		# Create the opened
		oOpened['_ticket'] = sID
		oOpened.create()

		# If we have sub items, add the real ID to each and create
		if lItems:
			for o in lItems:
				o['ticket'] = sID
				o.create()

		# Return the ID of the new ticket
		return Services.Response(sID)

	def ticket_delete(self, data, sesh):
		"""Ticket Delete

		Deletes a ticket if it was recently created or if the user has rights
		to do so

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [('_id', 'missing')])

		# Find the ticket
		oTicket = Ticket.get(data['_id'])
		if not oTicket:
			return Services.Error(1104)

		# If the ticket is older than a minute
		if oTicket['_created'] - int(time()) > 60:

			# Check permissions
			Rights.check(sesh, 'csr_overwrite', Rights.CREATE)

		# Delete the opened
		TicketOpened.deleteGet(data['_id'])

		# Delete the actions
		TicketAction.deleteGet(data['_id'], 'ticket')

		# Delete the items
		TicketItem.deleteGet(data['_id'], 'ticket')

		# Delete the resolved
		TicketResolved.deleteGet(data['_id'])

		# Delete the ticket
		oTicket.delete()

		# Return OK
		return Services.Response(True)

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
		Rights.internalOrCheck(data, sesh, ['csr_claims', 'order_claims'], Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['ticket', 'name', 'type'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If the ticket doesn't exist
		if not Ticket.exists(data['ticket']):
			return Services.Error(1104)

		# Make sure the name is valid
		if data['name'] not in TicketAction.types:
			return Services.Error(1001, [('type', 'invalid')])

		# Make sure the type is valid
		if data['type'] not in TicketAction.types[data['name']]:
			return Services.Error(1001, [('type', 'invalid')])

		# Add the memo ID from the session
		data['memo_id'] = sesh['memo_id']

		# Create a new instance
		try:
			oAction = TicketAction(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Store the data and return the result
		return Services.Response(
			oAction.create()
		)

	def ticketDetails_read(self, data, sesh):
		"""Ticket Details

		Returns all the details associated with the ticket in chronological
		order

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check rights
		Rights.check(sesh, ['csr_overwrite', 'csr_claims'], Rights.CREATE)

		# Check ID is passed
		if '_id' not in data:
			return Services.Error(1001, [('_id', 'missing')])

		# Make sure the ticket exists
		if not Ticket.exists(data['_id']):
			return Services.Error(1104)

		# Start the set of user IDs
		lUserIDs = set()

		# Start the list of details
		lDetails = []

		# Get the opened state
		dOpened = TicketOpened.get(data['_id'], raw=['_created', 'type', 'memo_id'])
		lUserIDs.add(dOpened['memo_id'])
		dOpened['_id'] = '%s-opened' % data['_id']
		dOpened['msgType'] = 'action'
		dOpened['name'] = 'Opened'
		lDetails.append(dOpened)

		# Get the actions
		lActions = TicketAction.filter({"ticket": data['_id']}, raw=['_id', '_created', 'name', 'type', 'memo_id'])
		for d in lActions:
			d['msgType'] = 'action'
			d['type'] = TicketAction.typeText(d['name'], d['type'])
			lDetails.append(d)

		# Get the resolved state
		dResolved = TicketResolved.get(data['_id'], raw=['_created', 'type', 'memo_id'])
		if dResolved:
			lUserIDs.add(dResolved['memo_id'])
			dResolved['_id'] = '%s-resolved' % data['_id']
			dResolved['msgType'] = 'action'
			dResolved['name'] = 'Resolved'
			lDetails.append(dResolved)

		# Fetch all the user names
		oResponse = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": list(lUserIDs)
		}, sesh)

		# Convert the IDs
		dMemoNames = DictHelper.keysToInts(oResponse.data)

		# Go through each detail and add the name
		for d in lDetails:
			try: dName = dMemoNames[d['memo_id']]
			except KeyError: dName = {"firstName": 'NAME', "lastName": 'MISSING'}
			d['created_by'] = '%s %s' % (dName['firstName'], dName['lastName'])

		# Init the types of items
		dItemTypes = {
			"email": [],
			"jc_call": [],
			"jc_sms": [],
			"note": [],
			"sms": []
		}

		# Get the items
		lItems = TicketItem.filter({"ticket": data['_id']}, raw=['type', 'identifier'])
		for d in lItems:
			dItemTypes[d['type']].append(int(d['identifier']))

		# Init the memo call data
		dData = {}
		if dItemTypes['sms']:
			dData['messages'] = dItemTypes['sms']
		if dItemTypes['note']:
			dData['notes'] = dItemTypes['note']

		# If we have any data
		if dData:

			# Fetch the sms and notes from monolith
			dData['_internal_'] = Services.internalKey()
			oResponse = Services.read('monolith', 'internal/ticketInfo', dData)

			# If we have messages
			if 'messages' in oResponse.data:
				for d in oResponse.data['messages']:
					d['_created'] = d['createdAt']
					d['msgType'] = 'sms'
					lDetails.append(d)

			# If we have notes
			if 'notes' in oResponse.data:
				for d in oResponse.data['notes']:
					d['_created'] = d['createdAt']
					d['msgType'] = 'note'
					lDetails.append(d)

		# If we have any JustCall calls
		if dItemTypes['jc_call']:

			# Fetch the logs from JustCall
			oResponse = Services.read('justcall', 'log', {
				"_internal_": Services.internalKey(),
				"id": dItemTypes['jc_call']
			}, sesh)

			print(oResponse.data)

			# If we have data
			if oResponse.data:
				for d in oResponse.data:
					d['msgType'] = 'justcall'
					d['_created'] = arrow.get('%s+00:00' % d['time_utc']).int_timestamp
					lDetails.append(d)

		# Sort the details by created timestamp
		lDetails.sort(key=itemgetter('_created'))

		# Return all the details
		return Services.Response(lDetails)

	def ticketExists_read(self, data):
		"""Ticket Exists

		Internal only request to validate a ticket ID

		Arguments:
			data (mixed): Data sent with the request

		Returns:
			Services.Response
		"""

		# Check rights
		Rights.internal(data)

		# If the ID is missing
		if '_id' not in data:
			return Services.Error(1001, [('_id', 'missing')])

		# Check for the record and return the result
		return Services.Response(
			Ticket.exists(data['_id'])
		)

	def ticketItem_create(self, data, sesh):
		"""Ticket Item Create

		Adds an item to an existing ticket

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check internal key or rights
		Rights.internalOrCheck(data, sesh, ['csr_claims', 'order_claims'], Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['ticket'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If the ticket doesn't exist
		if not Ticket.exists(data['ticket']):
			return Services.Error(1104)

		# Make sure the identifier is a string
		if 'identifier' in data:
			data['identifier'] = str(data['identifier'])

		# Create a new instance
		try:
			oItem = TicketItem(data)
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Create the item and check for duplicates
		try:
			return Services.Response(oItem.create())
		except Record_MySQL.DuplicateException:
			return Services.Error(1101)

	def ticketItemIds_read(self, data, sesh):
		"""Ticket Item IDs

		Returns just the IDs for all the items in the current ticket. Helpful
		for knowing if an item is in the current ticket

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check internal key or rights
		Rights.check(sesh, ['csr_claims', 'order_claims'], Rights.CREATE)

		# If the id is missing
		if '_id' not in data:
			return Services.Error(1001, [('_id', 'missing')])

		# Fetch all the items in the ticket
		return Services.Response([
			d for d in TicketItem.filter({
				"ticket": data['_id']
			}, raw=['type', 'identifier'])
		])

	def ticketOpenUser_read(self, data, sesh):
		"""Ticket Open User Read

		Returns if the given phone number or customer ID already has a ticket
		associated or not. Returns the ID of the ticket, else False

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check internal key or rights
		Rights.internalOrCheck(data, sesh, ['csr_claims', 'order_claims'], Rights.CREATE)

		# Init the filter
		dFilter = {}

		# If we have a CRM type and ID
		if 'crm_type' in data and 'crm_id' in data:
			dFilter['crm_type'] = data['crm_type']
			dFilter['crm_id'] = str(data['crm_id'])

		# Else, if we have a phone number
		elif 'phone_number' in data:
			dFilter['phone_number'] = data['phone_number']

		# Else, invalid data
		else:
			return Services.Error(1001, [('crm_type', 'missing'), ('crm_id', 'missing')])

		# Find the ticket
		mID = Ticket.unresolved(dFilter)

		# Return the ID or false
		return Services.Response(
			mID and mID or False
		)

	def ticketResolve_update(self, data, sesh):
		"""Ticket Resolve Update

		Resolves an existing ticket

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Check rights
		Rights.check(sesh, ['csr_claims', 'order_claims'], Rights.CREATE)

		# Verify minimum fields
		try: DictHelper.eval(data, ['_id', 'type'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Find the ticket
		dTicket = Ticket.get(data['_id'], raw=['_created', 'phone_number'])
		if not dTicket:
			return Services.Error(1104)

		# Create a new instance
		try:
			oResolved = TicketResolved({
				"_ticket": data['_id'],
				"type": data['type'],
				"memo_id": sesh['memo_id']
			})
		except ValueError as e:
			return Services.Error(1001, e.args[0])

		# Check for incoming SMS messages to add
		oResponse = Services.read('monolith', 'internal/incoming_sms', {
			"_internal_": Services.internalKey(),
			"customerPhone": dTicket['phone_number'],
			"start": dTicket['_created'],
			"end": int(time())
		})
		if oResponse.errorExists():
			return oResponse

		# If we have any messages
		if oResponse.data:
			TicketItem.addSMS(data['_id'], oResponse.data)

		# Try to create the ticket
		try:

			# Store the data and return the result
			return Services.Response(
				oResolved.create()
			)

		# If we get a duplicate exception
		except Record_MySQL.DuplicateException:
			return Services.Error(1101)

	def tickets_read(self, data, sesh):
		"""Tickets by User

		Returns all the tickets a user has any action on

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# If there's no memo_id in the session
		if 'memo_id' not in sesh:

			# Check rights
			Rights.check(sesh, 'csr_overwrite', Rights.READ)

			# If an agent type is passed
			if 'agent_type' in data:

				# Find the ids of all agents with the type
				lIDs = Agent.memoIdsByType(data['agent_type'])
				if lIDs:
					data['memo_id'] = lIDs
				else:
					return Services.Response([])

		# Else,
		else:

			# If the user is not sent, or not the one signed in
			if 'memo_id' not in data or data['memo_id'] != sesh['memo_id']:
				return Services.Error(Rights.INVALID)

		# Verify minimum fields
		try: DictHelper.eval(data, ['start', 'end'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Get a list of the unique tickets IDS the user is associated with
		lTicketIDs = Ticket.idsByRange(
			data['start'], data['end'],
			'memo_id' in data and data['memo_id'] or None
		)

		# Fetch the tickets by IDs with the opened and resolved info if any
		#	exists
		lTickets = Ticket.withState(lTicketIDs)

		# If there's no tickets
		if not lTickets:
			return Services.Response([])

		# Fetch all the user IDs
		lUsersIDs = set()
		for d in lTickets:
			lUsersIDs.add(d['opened_user'])
			if d['resolved_user']:
				lUsersIDs.add(d['resolved_user'])

		# Fetch their names
		oResponse = Services.read('monolith', 'user/name', {
			"_internal_": Services.internalKey(),
			"id": list(lUsersIDs)
		}, sesh)

		# Convert the IDs
		dMemoNames = DictHelper.keysToInts(oResponse.data)

		# Add the names to the agents
		for d in lTickets:
			try: dName = dMemoNames[d['opened_user']]
			except KeyError: dName = {"firstName": 'NAME', "lastName": 'MISSING'}
			d['opened_by'] = '%s %s' % (dName['firstName'], dName['lastName'])
			if d['resolved_user']:
				try: dName = dMemoNames[d['resolved_user']]
				except KeyError: dName = {"firstName": 'NAME', "lastName": 'MISSING'}
				d['resolved_by'] = '%s %s' % (dName['firstName'], dName['lastName'])
			else:
				d['resolved_by'] = None

		# Return the tickets
		return Services.Response(lTickets)

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
		Rights.check(sesh, ['csr_claims', 'order_claims'], Rights.CREATE)

		# If we have crm type and ID
		if 'crm_type' in data and 'crm_id' in data:
			dFilter = {
				"crm_type": data['crm_type'],
				"crm_id": str(data['crm_id'])
			}

		# Else, if we got a phone number
		elif 'phone_number' in data:
			dFilter = {
				"phone_number": data['phone_number']
			}

		# Else, missing data
		else:
			return Services.Error(1001, [('crm_type', 'missing'), ('crm_id', 'missing')])

		# Find all the record IDs
		lTickets = Ticket.filter(dFilter, raw=['_id'], orderby='_created')

		# If we have no tickets
		if not lTickets:
			return Services.Response([])

		# Get the tickets with the state
		lTickets = Ticket.withState([d['_id'] for d in lTickets])

		# Fetch all the user IDs
		lUsersIDs = set()
		for d in lTickets:
			lUsersIDs.add(d['opened_user'])
			if d['resolved_user']:
				lUsersIDs.add(d['resolved_user'])

		# If there's IDs
		if lUsersIDs:

			# Fetch their names
			oResponse = Services.read('monolith', 'user/name', {
				"_internal_": Services.internalKey(),
				"id": list(lUsersIDs)
			}, sesh)

			# Convert the IDs
			dMemoNames = DictHelper.keysToInts(oResponse.data)

		# Else,
		else:
			dMemoNames = {}

		# Add the names to the agents
		for d in lTickets:
			try: dName = dMemoNames[d['opened_user']]
			except KeyError: dName = {"firstName": 'NAME', "lastName": 'MISSING'}
			d['opened_by'] = '%s %s' % (dName['firstName'], dName['lastName'])
			if d['resolved_user']:
				try: dName = dMemoNames[d['resolved_user']]
				except KeyError: dName = {"firstName": 'NAME', "lastName": 'MISSING'}
				d['resolved_by'] = '%s %s' % (dName['firstName'], dName['lastName'])
			else:
				d['resolved_by'] = None

		# Return the tickets
		return Services.Response(lTickets)

	def ticketStats_read(self, data, sesh):
		"""Ticket Stats

		Fetches the stat for the specified user and type by each range passed

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['memo_id', 'ranges', 'type'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# If there's no memo_id in the session
		if 'memo_id' not in sesh:

			# Check rights
			Rights.check(sesh, 'csr_overwrite', Rights.READ)

		# Else,
		else:

			# If the user is not sent, or not the one signed in
			if data['memo_id'] != sesh['memo_id']:
				return Services.Error(Rights.INVALID)

		# If ranges is not a list
		if not isinstance(data['ranges'], dict):
			return Services.Error(1001, [('ranges', 'not an object')])

		# If the type is opened
		if data['type'] == 'opened':
			RecordClass = TicketOpened

		# Else, if the type is resolved
		elif data['type'] == 'resolved':
			RecordClass = TicketResolved

		# Else, we received an invalid class
		else:
			return Services.Error(1001, [('type', 'invalid')])

		# Init the return dict
		dRet = {}

		# Go through each range and fetch the counts
		for k in data['ranges']:

			# If ranges is not a list
			if not isinstance(data['ranges'][k], list):
				return Services.Error(1001, [('ranges.%s' % str(k), 'not a list')])

			# Fetch the count and store it by key
			dRet[k] = RecordClass.countByUser(
				data['memo_id'],
				data['ranges'][k]
			)

		# Return the results
		return Services.Response(dRet)

	def ticketStatsGraph_read(self, data, sesh):
		"""Ticket Stats Graph

		Fetches the stats for the given group/user in the given range

		Arguments:
			data (mixed): Data sent with the request
			sesh (Sesh._Session): The session associated with the request

		Returns:
			Services.Response
		"""

		# Verify minimum fields
		try: DictHelper.eval(data, ['range_type', 'range'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Init the filter
		dFilter = {
			"range": data['range_type'],
			"date": {"between": data['range']}
		}

		# If there's no memo_id in the session
		if 'memo_id' not in sesh:

			# Check rights
			Rights.check(sesh, 'csr_overwrite', Rights.READ)

			# If an agent type is passed
			if 'agent_type' in data:
				dFilter['list'] = data['agent_type']

			# If a memo user is passed
			elif 'memo_id' in data:
				dFilter['memo_id'] = data['memo_id']

			# Else, bad data
			else:
				return Services.Error(1001, [('agent_type', 'missing')])

		# Else,
		else:

			# If the user is not sent, or not the one signed in
			if 'memo_id' not in data or data['memo_id'] != sesh['memo_id']:
				return Services.Error(Rights.INVALID)

			# Store the memo ID in the filter
			dFilter['memo_id'] = data['memo_id']

		# If we have an action type passed, add it to the filter
		if 'action' in data:
			dFilter['action'] = data['action']

		# Fetch the stats
		lStats = TicketStat.filter(dFilter, raw=['date', 'action', 'count'])

		# Create a new dict for storing the action types
		dRet = {}

		# Create a set of dates
		lDates = set()

		# Go through each stat
		for d in lStats:

			# Store the date
			lDates.add(d['date'])

			# Add to the appropriate action
			try: dRet[d['action']][d['date']] = d['count']
			except KeyError: dRet[d['action']] = {d['date']: d['count']}

		# Added the sorted list of dates
		dRet['dates'] = sorted(list(lDates))

		# Go through each action
		for k in dRet:

			# Go through each date
			for s in lDates:

				# If we're missing the count
				if s not in dRet[k]:
					dRet[k][s] = 0

		# Return the stats by action
		return Services.Response(dRet)
