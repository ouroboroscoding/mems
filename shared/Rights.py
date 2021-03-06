# coding=utf8
""" Permission Rights

Defines for Rights types
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexecl.com"
__created__		= "2020-04-02"

# Pip imports
from RestOC import Errors, Services

READ	= 0x01
"""Allowed to read records"""

UPDATE	= 0x02
"""Allowed to update records"""

CREATE	= 0x04
"""Allowed to create records"""

DELETE	= 0x08
"""Allowed to delete records"""

ALL		= 0x0F
"""Allowed to CRUD"""

INVALID = 1000
"""REST invalid rights error code"""

def check(sesh, name, right, ident=None):
	"""Check

	Checks's if the currently signed in user has the requested right on the
	given permission. If the user has rights, nothing happens, else an
	exception of ResponseException is raised

	Arguments:
		sesh (RestOC.Sesh._Session): The current session
		name (str): The name of the permission to check
		right (uint): The right to check for
		ident (str): Optional identifier to check against

	Raises:
		ResponseException

	Returns:
		None
	"""

	# Init request data
	dData = {
		"name": name,
		"right": right
	}

	# If we have an ident, add it on
	if ident is not None:
		dData['ident'] = ident

	# Check with the auth service
	oResponse = Services.read('auth', 'rights/verify', dData, sesh)

	# If the check failed, raise an exception
	if not oResponse.data:
		raise Services.ResponseException(error=INVALID)

	# Return OK
	return True

def checkReturn(sesh, name, right, ident=None):
	""" Check Return

	Same as check, but returns the result instead of raising an exception

	Arguments:
		sesh (RestOC.Sesh._Session): The current session
		name (str): The name of the permission to check
		right (uint): The right to check for
		ident (str): Optional identifier to check against

	Returns:
		bool
	"""

	try:
		check(sesh, name, right, ident)
		return True
	except Services.ResponseException:
		return False

def internal(data):
	""" Internal

	Checks for an internal key and throws an exception if it's missing or
	invalid

	Arguments:
		data (dict): Data to check for internal key

	Raises:
		ResponseException

	Returns:
		None
	"""

	# If the key is missing
	if '_internal_' not in data:
		raise Services.ResponseException(error=(1001, [('_internal_', 'missing')]))

	# Verify the key, remove it if it's ok
	if not Services.internalKey(data['_internal_']):
		raise Services.ResponseException(error=Errors.SERVICE_INTERNAL_KEY)
	del data['_internal_']

def internalOrCheck(data, sesh, name, right, ident=None):
	""" Internal or Check

	Checks for an internal key, if it wasn't sent, does a rights check

	Arguments:
		data (dict): Data to check for internal key
		sesh (RestOC.Sesh._Session): The current session
		name (str): The name of the permission to check
		right (uint): The right to check for
		ident (str): Optional identifier to check against

	Raises:
		ResponseException

	Returns:
		None
	"""

	# If this is an internal request
	if '_internal_' in data:

		# Verify the key, remove it if it's ok
		if not Services.internalKey(data['_internal_']):
			raise Services.ResponseException(error=Errors.SERVICE_INTERNAL_KEY)
		del data['_internal_']

	# Else,
	else:

		# If there's no session
		if not sesh:
			return Services.Error(Errors.REST_AUTHORIZATION, 'Unauthorized')

		# Make sure the user has the proper permission to do this
		check(sesh, name, right, ident)
