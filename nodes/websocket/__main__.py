# coding=utf8
""" WebSocket Node

Handles syncing up changes using websockets and sessions
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2017-06-26"

# Import python modules
from collections import OrderedDict
import os
import platform
import threading

# Import pip modules
from gevent import monkey; monkey.patch_all()
from geventwebsocket import Resource, WebSocketServer
from RestOC import Conf

# Load the config
Conf.load('config.json')
sConfOverride = 'config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Import module
from . import init as wsInit, stop as wsStop, thread as wsThread, SyncApplication

# If verbose mode is requested
verbose	= False
if 'VERBOSE' in os.environ and os.environ['VERBOSE'] == '1':
	verbose	= True

# Init the sync application
wsInit(verbose)

# Start the Redis thread
try:
	if verbose: print('Starting the Redis thread')
	thread = threading.Thread(target=wsThread)
	thread.daemon = True
	thread.start()
except Exception as e:
	print('Failed to start Redis thread: %s' % str(e))

# Get the host and port
dConf = Conf.get('websocket', {
	"host": "0.0.0.0",
	"port": 8001
})

# Create the websocket server
if verbose: print('Starting the WebSocket server on %s:%d' % (dConf['host'], dConf['port']))
server = WebSocketServer(
	(dConf['host'], dConf['port']),
	Resource(OrderedDict([('/',SyncApplication)]))
)

try:
	server.serve_forever()
except KeyboardInterrupt:
	wsStop()
	pass

server.close()
