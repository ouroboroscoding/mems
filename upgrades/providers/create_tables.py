# coding=utf8
""" Create the Products tables"""

# Services
from records.providers import Provider, TemplateEmail, TemplateSMS
from records.qualmed import KnkOrder

def run():

	# Create the tables
	KnkOrder.tableCreate()
	Provider.tableCreate()
	TemplateEmail.tableCreate()
	TemplateSMS.tableCreate()

	# Return OK
	return True
