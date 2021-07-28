# coding=utf8
""" Create the monolith `customer_reviews` table"""

# Services
from records.monolith import CustomerReviews

def run():

	# Create the tables
	CustomerReviews.tableCreate()

	# Return OK
	return True
