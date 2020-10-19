# coding=utf8
""" Create the Products tables"""

# Services
from records.providers import Provider, TemplateEmail, TemplateSMS

def run():

	# Create the tables
	Provider.tableCreate()
	TemplateEmail.tableCreate()
	TemplateSMS.tableCreate()

	# Return OK
	return True
