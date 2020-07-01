# coding=utf8
""" Install Services

Adds global tables
"""

# Python imports
import os, platform

# Framework imports
from RestOC import Conf, Record_MySQL

# Services
from services import auth, csr, payment

# Only run if called directly
if __name__ == "__main__":

	# Load the config
	Conf.load('../config.json')
	sConfOverride = '../config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Add hosts
	Record_MySQL.addHost('primary', Conf.get(("mysql", "hosts", "primary")))

	# Add the DBs
	Record_MySQL.dbCreate(Conf.get(("mysql", "primary", "db"), "mems"), 'primary', 'utf8mb4', 'utf8mb4_bin')

	# Install
	auth.Auth.install()
	payment.Payment.install()
	csr.CSR.install()

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
