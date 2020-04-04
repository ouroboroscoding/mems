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
oUser = auth.records.User({
	"email": "admin@maleexcel.com",
	"passwd": auth.records.User.passwordHash('Admin123'),
	"locale": "en-US",
	"firstName": "Admin",
	"lastName": "Istrator"
})
sUserId = oUser.create(changes={"user": "system"})

# Add admin permission
auth.records.Permission.createMany([
	auth.records.Permission({"user": sUserId, "name": "user", "rights": 15}),
	auth.records.Permission({"user": sUserId, "name": "permission", "rights": 15})
])
