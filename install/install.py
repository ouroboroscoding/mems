# coding=utf8
""" Install Services

Adds global tables
"""

# Python imports
import os, platform

# Framework imports
from RestOC import Conf, Record_MySQL

# Services
from records.auth import Permission, User
import services

# Only run if called directly
if __name__ == "__main__":

	# Load the config
	Conf.load('config.json')
	sConfOverride = 'config.%s.json' % platform.node()
	if os.path.isfile(sConfOverride):
		Conf.load_merge(sConfOverride)

	# Add hosts
	Record_MySQL.addHost('primary', Conf.get(("mysql", "hosts", "primary")))

	# Add the DBs
	Record_MySQL.dbCreate(Conf.get(("mysql", "primary", "db"), "mems"), 'primary', 'utf8', 'utf8_bin')

	# Install
	services.auth.Auth.install()
	services.csr.CSR.install()
	services.customers.CSR.install()
	services.patient.Patient.install()
	services.payment.Payment.install()
	services.prescriptions.Prescriptions.install()
	services.reports.Reports.install()
	services.welldyne.WellDyne.install()

	# Install admin
	oUser = User({
		"email": "admin@maleexcel.com",
		"passwd": User.passwordHash('Admin123'),
		"locale": "en-US",
		"firstName": "Admin",
		"lastName": "Istrator"
	})
	sUserId = oUser.create(changes={"user": "system"})

	# Add admin permission
	Permission.createMany([
		Permission({"user": sUserId, "name": "user", "rights": 15}),
		Permission({"user": sUserId, "name": "permission", "rights": 15})
	])
