UPDATE `%(db)s`.`%(table)s` SET
	`lastMsgDir` = '%(direction)s',
	`lastMsgAt` = '%(date)s',
	`hiddenFlag` = '%(hidden)s',
	`%(increment)s` = `%(increment)s` + 1,
	`lastMsg` = CONCAT('%(message)s', IFNULL(`lastMsg`, ''))
WHERE `customerPhone` = '%(customerPhone)s'
