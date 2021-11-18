# coding=utf8
"""Shipping

Handles shared shipping/tracking functions
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2020-09-01"

TRACKING_LINKS = {
	"FDX": "https://www.fedex.com/fedextrack/?trknbr=%s",
	"UPS": "https://www.ups.com/track?tracknum=%s",
	"USPS": "https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1=%s"
}

def generateLink(type_, code):
	"""Generate Links

	Generates a usable tracking code URL

	Arguments:
		type_ (str): The type of tracking code
		code (str): The tracking code

	Returns:
		str
	"""

	try:
		return TRACKING_LINKS[type_] % code;
	except Exceptions:
		return None;
