# coding=utf8
"""Link Clear

Clears out data associated with links that no longer work
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-03-08"

# Pip imports
from RestOC import Record_MySQL

# Record imports
from records.link import UrlRecord, ViewRecord

def run():

	# Find all records that haven't been accessed in 30 days
	lIDs = [d['_id'] for d in UrlRecord.filter({
		"_updated": {"lt": Record_MySQL.Literal('DATE_SUB(NOW(), INTERVAL 30 DAY)')}
	}, raw=['_id'])]

	# If we have no IDs
	if not lIDs:
		return True

	# Delete all views
	ViewRecord.deleteByUrl(lIDs)

	# Delete all URLs
	UrlRecord.deleteGet(lIDs)

	# Return OK
	return True
