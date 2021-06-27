# coding=utf8
""" Update all the ticket item records to add the direction and memo ID"""

# Pip imports
from RestOC import Record_MySQL

# Service imports
from services.justcall import JustCall

# Record imports
from records.justcall import MemoId
from records.monolith import CustomerCommunication, SmpNote

# Names to IDs
dNamesToIds = {}

def run():

	# Create a JustCall instance
	oJustCall = JustCall()
	oJustCall.initialise()

	# Loop forever
	while True:

		# Find a NULL direction
		dItem = Record_MySQL.Commands.select(
			"primary",
			"SELECT `_id`, `type`, `identifier` " \
			"FROM `mems`.`csr_ticket_item` " \
			"WHERE `direction` IS NULL",
			Record_MySQL.ESelect.ROW
		)

		# If there's none, we're done
		if not dItem:
			break

		# If it's an JustCall log
		if dItem['type'] == 'jc_call':

			# Find the log
			dCall = oJustCall._one('calls/get', {
				"id": int(dItem['identifier'], 10)
			})

			# If there's no call
			if not dCall:
				print('!!! ERROR !!!')
				print('No JustCall log found for %s' % dItem['identifier'])
				return False

			# If it's outbound
			if dCall['type'] == '2':

				# Set the direction
				sDirection = 'outgoing'

				# Look for the memo user using the agent ID
				dMemoId = MemoId.get(dCall['agent_id'], raw=['memo_id'])

				# If no ID is found
				if not dMemoId:
					print('!!! ERROR !!!')
					print('No user found for agent_id %d' % dCall['agent_id'])
					return False

				# Store the memo id
				iMemoId = dMemoId['memo_id']

			# Else, it's some sort of inbound
			else:
				sDirection = 'incoming'
				iMemoId = 0

		# If it's a note
		elif dItem['type'] == 'note':

			# Fetch the note
			dNote = SmpNote.get(int(dItem['identifier'], 10), raw=['action', 'createdBy'])

			# If there's no note
			if not dNote:
				print('!!! ERROR !!!')
				print('No smp_note found for %s' % dItem['identifier'])
				return False

			# If it's a customer sms to a dr.
			if dNote['action'] == 'Receive Communication':
				sDirection = 'incoming'
				iMemoId = 0

			# Else it has to be outgoing
			else:
				sDirection = 'outgoing'
				iMemoId = dNote['createdBy']

		# If it's an SMS
		elif dItem['type'] == 'sms':

			# Fetch the sms
			dSMS = CustomerCommunication.get(int(dItem['identifier'], 10), raw=['type', 'fromName'])

			# If there's no SMS
			if not dSMS:
				print('!!! ERROR !!!')
				print('No smp_note found for %s' % dItem['identifier'])
				return False

			# If it's incoming
			if dSMS['type'] == 'Incoming':
				sDirection = 'incoming'
				iMemoId = 0

			# Else it's outgoing
			else:

				# Set the direction
				sDirection = 'outgoing'

				# If we don't already have the ID
				if dSMS['fromName'] not in dNamesToIds:
					iID = Record_MySQL.Commands.select(
						'monolith',
						"SELECT `id` " \
						"FROM `monolith`.`user` " \
						"WHERE CONCAT(`firstName`, ' ', `lastName`) = '%s'" % dSMS['fromName'],
						Record_MySQL.ESelect.CELL
					)

					# If no ID is found
					if not iID:
						print('!!! ERROR !!!')
						print('No user found for sms %s' % dSMS['fromName'])
						return False

					# Store the user ID by the name
					dNamesToIds[dSMS['fromName']] = iID

				# Set the memo ID
				iMemoId = dNamesToIds[dSMS['fromName']]

		# Update the record
		Record_MySQL.Commands.execute(
			'primary',
			"UPDATE `mems`.`csr_ticket_item` SET " \
			"`direction` = '%s', " \
			"`memo_id` = %d " \
			"WHERE `_id` = '%s'" % (
				sDirection, iMemoId, dItem['_id']
			)
		)

	# Return OK
	return True
