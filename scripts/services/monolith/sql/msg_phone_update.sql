UPDATE `%(db)s`.`%(table)s` SET
	`lastMsgDir` = 'Outgoing',
	`lastMsgAt` = '%(date)s',
	`hiddenFlag` = 'Y',
	`totalOutGoing` = `totalOutGoing` + 1,
	`lastMsg` = CONCAT('%(message)s', IFNULL(`lastMsg`, ''))
WHERE `customerPhone` = '%(customerPhone)s'
