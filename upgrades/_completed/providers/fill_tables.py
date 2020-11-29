# coding=utf8
""" Fill tables"""

# Pip imports
from RestOC import Record_MySQL

def run():

	# Insert the campaigns
	Record_MySQL.Commands.execute(
		'monolith',
		'INSERT INTO `monolith`.`campaign` (`id`, `type`) VALUES ' \

		"(2, 'ed'), (4, 'ed'), (5, 'ed'), (7, 'ed'), " \
		"(8, 'ed'), (9, 'ed'), (11, 'ed'), (12, 'ed'), " \
		"(14, 'ed'), (16, 'ed'), (17, 'ed'), (20, 'ed'), " \
		"(21, 'ed'), (22, 'ed'), (23, 'ed'), (24, 'ed'), " \
		"(25, 'ed'), (27, 'ed'), (28, 'ed'), (31, 'ed'), " \
		"(32, 'ed'), (34, 'ed'), (35, 'ed'), (37, 'ed'), " \
		"(38, 'ed'), (39, 'ed'), (42, 'ed'), (43, 'ed'), " \
		"(45, 'ed'), (46, 'ed'), (47, 'ed'), (49, 'ed'), " \
		"(50, 'ed'), (52, 'ed'), (53, 'ed'), (55, 'ed'), " \
		"(56, 'ed'), (58, 'ed'), (59, 'ed'), (60, 'ed'), " \
		"(61, 'ed'), (62, 'ed'), (63, 'ed'), (64, 'ed'), " \
		"(65, 'ed'), (66, 'ed'), (67, 'ed'), (68, 'ed'), " \
		"(69, 'ed'), (70, 'ed'), (71, 'ed'), (73, 'ed'), " \
		"(74, 'ed'), (75, 'ed'), (76, 'ed'), (79, 'ed'), " \
		"(80, 'ed'), (81, 'ed'), (82, 'ed'), (83, 'ed'), " \
		"(84, 'ed'), (85, 'ed'), (86, 'ed'), (87, 'ed'), " \
		"(88, 'ed'), (89, 'ed'), (90, 'ed'), (91, 'ed'), " \
		"(94, 'ed'), (95, 'ed'), (96, 'ed'), (97, 'ed'), " \
		"(98, 'ed'), (99, 'ed'), (100, 'ed'), (101, 'ed'), " \
		"(102, 'ed'), (104, 'ed'), (105, 'ed'), (106, 'ed'), " \
		"(107, 'ed'), (108, 'ed'), (109, 'ed'), (110, 'ed'), " \
		"(112, 'ed'), (114, 'ed'), (115, 'ed'), (122, 'ed'), " \
		"(125, 'ed'), " \

		"(121, 'hrt'), (123, 'hrt'), (127, 'hrt'), " \

		"(116, 'zrt'), (119, 'zrt'), (124, 'zrt');"
	)

	# Insert the report recipients for missing campaigns
	Record_MySQL.Commands.execute(
		'primary',
		"INSERT INTO `mems`.`reports_recipients` (`_id`, `name`, `addresses`)\n" \
		"VALUES (UUID(), 'Campaigns_Missing', 'bast@maleexcel.com');"
	)

	# Return OK
	return True
