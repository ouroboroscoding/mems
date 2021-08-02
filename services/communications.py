# coding=utf8
""" Communications Service

Manages communications, email, sms, etc
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-03-30"

# Python imports
from base64 import b64decode
from hashlib import md5

# Pip imports
from RestOC import Conf, DictHelper, Errors, Services, SMTP, StrHelper
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

class Service(Services.Service):
	"""Service

	The Communications class that extends the base Service class
	"""

	def __init__(self):
		"""Constructor

		Initialises the object

		Returns:
			Service
		"""

		# Key for encrypting messages between communications and queue
		self._queue_key = None

		# Twilio client
		self._twilio = None
		self._smsServices = {}

	def _queueKey(self, data, key=None):
		"""Queue Key

		If nothing is passed, we are generating the key, else we are validating
		it

		Arguments:
			data (dict): The data that was passed or retrieved
			key (str): The key to validate if passed

		Returns:
			str|bool
		"""

		# Turn the data into a str and md5 it
		sMD5 = md5(str(data).encode('utf-8')).hexdigest()

		# If a key was received
		if key:

			# Decode it and see if it matches the data
			return StrHelper.decrypt(self._queue_key, key) == sMD5

		# Else
		else:

			# Generate and return a key
			return StrHelper.encrypt(self._queue_key, sMD5)

	def create(self, path, data, sesh=None, environ=None):
		"""Create

		Overrides base create so we can manage direct requests vs queued

		Arguments:
			path (str): The path/noun of the request
			data (mixed): The data passed with the request
			sesh (Sesh._Session): Not used
			environ (dict): Info related to request

		Returns:
			Services.Response
		"""

		# If we are sending an email
		if path == 'email':
			return self.email(data)

		# If we are sending an sms
		if path == 'sms':
			return self.sms(data)

		# Invalid path
		return Services.Response(error=(Errors.SERVICE_NO_SUCH_NOUN, 'POST %s' % path))

	def email(self, data):
		"""Email

		Sends an e-mail, by either sending it to the queue, or sending it
		directly

		Arguments:
			data (dict): The data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'subject', 'to'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# Check that we have at least one type of body
		if 'html_body' not in data and 'text_body' not in data:
			return Services.Response(error=1300)

		# Add None if either body is missing
		if 'html_body' not in data:	data['html_body'] = None
		if 'text_body' not in data:	data['text_body'] = None

		# If the from is not set
		if 'from' not in data:
			data['from'] = self.fromDefault

		# If we got a _queue_ value
		if '_queue_' in data:

			# Store it
			sQueueKey = data.pop('_queue_')

			# If it's not valid
			if not self._queueKey(data, sQueueKey):
				return Services.Response(error=1001)

			# Else, we're good
			data['_queue_'] = True

		# If we are sending direct, or we got a valid request from the queue
		if self.emailMethod == 'direct' or '_queue_' in data:

			# Init the attachments var
			mAttachments = None

			# If there's an attachment
			if 'attachments' in data:

				# Make sure it's a list
				if not isinstance(data['attachments'], (list,tuple)):
					data['attachments'] = [data['attachments']]

				# Loop through the attachments
				for i in range(len(data['attachments'])):

					# If we didn't get a dictionary
					if not isinstance(data['attachments'][i], dict):
						return Services.Response(error=(1301, "attachments.%d" % i))

					# If the fields are missing
					try:
						DictHelper.eval(data['attachments'][i], ['body', 'filename'])
					except ValueError as e:
						return Services.Responses(error=(1001, [("attachments.%d.%s" % (i, s), 'invalid') for s in e.args]))

					# Try to decode the base64
					try:
						data['attachments'][i]['body'] = b64decode(data['attachments'][i]['body'])
					except TypeError:
						return Services.Response(error=1302)

				# Set the attachments from the data
				mAttachments = data['attachments']

			# Only send if anyone is allowed, or the to is in the allowed
			if not self.emailAllowed or data['to'] in self.emailAllowed:

				# Send the e-mail
				iRes = SMTP.send(
					data['to'], data['subject'],
					text_body=data['text_body'],
					html_body=data['html_body'],
					from_=data['from'],
					attachments=mAttachments
				)

				# If there was an error
				if iRes != SMTP.OK:
					return Services.Response(error=(1303, '%i %s' % (iRes, SMTP.lastError())))

		# Else, we are sending to the queue first
		else:

			# Add a queue key to the data
			data['_queue_'] = self._queueKey(data)

			# Send the data to the queue service
			oResponse = Services.create('queue', 'msg', {
				"_internal_": Services.internalKey(),
				"service": "communications",
				"path": "email",
				"method": "create",
				"data": data
			})

			# Return if there's an error
			if oResponse.errorExists():
				return oResponse

		# Return OK
		return Services.Response(True)

	def initialise(self):
		"""Initialise

		Initialises the communications service

		Returns:
			None
		"""

		# Set the queue key
		self._queue_key = Conf.get(('services', 'queue', 'key'))

		# Get the default from
		self.fromDefault = Conf.get(('email', 'from'))

		# Get the method for sending emails
		self.emailMethod = Conf.get(('email', 'method'))

		# If it's invalid
		if self.emailMethod not in ['direct']:
			raise ValueError('Communications.emailMethod', self.emailMethod)

		# Get allowed addresses
		self.emailAllowed = Conf.get(('email', 'allowed'), [])

		# Get allowed numbers
		self.smsAllowed = Conf.get(('sms', 'allowed'), [])

		# Create client
		self._twilio = Client(
			Conf.get(('twilio', 'account_sid')),
			Conf.get(('twilio', 'auth_token'))
		)

		# Store services
		self._smsServices = Conf.get(('twilio', 'services'))

	def sms(self, data):
		"""SMS

		Sends an SMS, by either sending it to the queue, or sending it
		directly

		Arguments:
			data (dict): The data sent with the request

		Returns:
			Services.Response
		"""

		# Verify fields
		try: DictHelper.eval(data, ['_internal_', 'to', 'content', 'service'])
		except ValueError as e: return Services.Response(error=(1001, [(f, 'missing') for f in e.args]))

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			return Services.Response(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

		# If the service is invalid
		if data['service'] not in self._smsServices:
			return Services.Response(error=(1001, [('service', 'invalid')]))

		try:

			# Only send if anyone is allowed, or the to is in the allowed
			if not self.smsAllowed or data['to'] in self.smsAllowed:
				dRes = self._twilio.messages.create(
					to=data['to'],
					body=data['content'],
					messaging_service_sid=self._smsServices[data['service']]
				)

				# Return the SID of the message
				return Services.Response(dRes.sid)

			# Return the SID of the message
			return Services.Response('not sent')

		except TwilioRestException as e:
			return Services.Response(error=(1304, str(e)))
