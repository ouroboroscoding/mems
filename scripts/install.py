# coding=utf8
""" Install Services

Adds global tables
"""

# Python imports
import os, platform

# Framework imports
from RestOC import Conf, Record_MySQL

# Services
from services import auth

# Load the config
Conf.load('../config.json')
sConfOverride = '../config.%s.json' % platform.node()
if os.path.isfile(sConfOverride):
	Conf.load_merge(sConfOverride)

# Add primary host
Record_MySQL.addHost('primary', Conf.get(("mysql", "hosts", "primary")))

# Add the DB
Record_MySQL.dbCreate(Conf.get(("mysql", "db"), "mems"))

# Install
auth.Auth.install()

# Install admin
oLogin = auth.records.Login({
	"email": "admin@maleexcel.com",
	"passwd": auth.records.Login.passwordHash('Admin123'),
	"locale": "en-US",
	"firstName": "Admin",
	"lastName": "Istrator"
})
oLogin.create(changes={"login": "system"})
