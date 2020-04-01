# Python imports
import sys

# Import the Auth service records
from services.auth.records import Login

# Get the length of arguments
iArgLen	= len(sys.argv)

# Check we got a valid argument
if iArgLen < 2:
	print('Must pass a list of passwords in order to have them hashed')
	exit(-1)

# Go through each argument and hash it appropriately
for i in range(1,iArgLen):

	print('%s: ' % sys.argv[i], end='')

	# Check it's valid
	if not Login.passwordStrength(sys.argv[i]):
		print('invalid')
	else:
		print('%s' % Login.passwordHash(sys.argv[i]))

print('Done')
