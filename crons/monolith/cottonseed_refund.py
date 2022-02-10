# coding=utf8
"""Cottonseed Refund

Due to screw ups in Memo customers were charged for the wrong product and need
to be refunded
"""

__author__		= "Chris Nasr"
__copyright__	= "MaleExcelMedical"
__version__		= "1.0.0"
__maintainer__	= "Chris Nasr"
__email__		= "bast@maleexcel.com"
__created__		= "2021-09-19"

# Python imports
from pprint import pprint

# Service imports
from services.konnektive import Konnektive

def run():
	"""Run

	Refund all the orders in the list

	Returns:
		bool
	"""

	lOrders = ['53972F3E0B', '7711A350CC', '8D60F53489', 'E628D38960', 'C767A8444E', '8E90AE6589', '5EACC4664B', '8874F7D3B5', '3A75CA366F', '140137AE58', '2594846610', '305ADE482D', 'D224BDE06A', '6517A0B2D8', '04CDD35051', 'D857539237', '9F4787632E', '14CDE19E50', 'FF9B6866E3', '625B80A37B', 'EB9CB58892', '3BF7CDB7AA', '9FF598F99E', 'ED00AA3018', '527D482C90', 'E28B6E662C', '78C8D71992', '77E15828A8', '2FAD372A90', 'FF8D71D391', '32CF306ABD', '362F801CA4', '03F751EE33', '9D8AEFA2D6', '376C8A4B52', 'AC397AFF8D', 'EDE7A04303', '65EBAAD762', 'B664143E8A', 'F6D47D051E', '3786168229', 'C54E9F3E70', 'FA575AF070', '2DA349AB3F', 'D114B7754D', '9849A018B8', 'F614CAA4E9', '279CA12C8B', 'A298E43CF3', '0BAB5F9326', 'C5D86D4780', '66C544F5A8', 'B686E873AA', '66DAE948CD', 'E87D6833F4', 'B69E46B694', 'B1B4F7FA0F', 'BBA1CDEC85', 'FC80EAA7F4', '4CD08354AE', '34BF4F38B3', 'DA51E5B436', 'D0FA4C5E62', 'CA83B05C7F', '52A42B38A1', '7707E12FAC', '771DD43A21', '066DEA3145', 'A185F83CD4', '2B60533BF3', '580061A30D', '321F37AF6D', 'F6F2BD8B64', 'AC247E9E5C', 'D91EFF437F', '18C527C375', 'FCFA5BB8E1', '9A270386F9', 'D5CFFF081E', 'A4DC6655DC', '22CC14A515', '7B16F1003B', '93517C1FD3', '5DBBD5CFAD', '2EF4BBA63B', 'BD6BCC29BA', 'A1ECF261E4', 'B11C395D86', '36C8E08B60', '2743CD386F', 'D443AE792E', 'E88C69887A', 'F63661F881', 'DA7BAD0763', '541887236B', 'D466E5E27F', 'F2FCDEA069', '64E3659E74', '63089250E4', '2963CA17C9', '879D7D3DEA', '1A5CF71E26', '2D1121962E', '66F2A62D4C', 'D42F1C3737', '59193F0378', '9686D5DEDE', '651EB0978B', '453D341ABF', 'E5C6CCA672', 'A31957AE26', 'E04427F001', 'B227BBA543', '3A810CA394', '95869ABD8F', 'F53B230F81', 'A54054746D', 'DBB2FA3DD1', '7D18E4B8C0', '8A13421870', '5A176B9D76', '171064D040', 'F4000DBD9F', '9EE08395A2', 'CFFE3A7507', '303FC5B04C', '30E5C6C9B4', '8897AC1DBE', '1DA7B90714', '8DEE2F3B47', '77D87C983A', 'FA3452967F', '9386F9079A', '7089C83CB6', 'DBD5DE81FB', '1D3E3BE60A', '4BFC8D64DD', '9CD5A5E436', 'AFDFFCEDC7', 'FEFD35953A', '4FBCD9F918', 'A6E47FC4A0', '1306BE682B', '310898270A', '2C5CB1322E', '521A966F5C', 'D01C5B97D0', 'EFEA652F66', 'CC955717CB', '9704947489', 'C8A9D58198', '90BF53C82E', '28D1A96BC0', '973A65E56A', 'ABE681C4F7', '9FAE479DCB', '1F7B37C008', '15ABDC4984', '1FCC5E342C', 'F517D5D52B', 'AFC2B0CAC5', 'F3221C952E', 'EE5E38F6D9', '23F4022310', '91F948BB7E', '1F4C94B45F', '454D9542E0', '6718FB8E68', 'B5B80EFF26', '086B4EB5AC', '6CCEFCE6CF', 'A75BB61E73', '509799E678', 'D32D3C0A30', 'D19CB6EA69', 'FFBA41A3A2', '752A394D5D', '5C971A4576', '0F2766020B', '7C346A6AFB', 'C32012A532', 'A498E450AD', '8F6E4F36BC', '2582153FD5', '5D8B1CC845', '1C4AB995A3', 'B0513F36AA', '1CD893A83E', '11694463F3', '563C843CF8']

	# Create a new Konnektive service then initialise it
	oKNK = Konnektive()
	oKNK.initialise()

	# Go through each order
	for orderId in lOrders:

		# Refund the order
		dRes = oKNK._post('order/refund', {
			"orderId": orderId,
			"refundAmount": '25.00',
			"cancelReason": "Memo Cottonseed Error"
		})

		# If we failed
		if dRes['result'] != 'SUCCESS':
			print('----------------------------------------')
			print(orderId)
			pprint(dRes)
			return False

	# Return OK
	return True