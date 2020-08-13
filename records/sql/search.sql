SELECT
	`cmp`.`id` AS `id`,
	`cmp`.`customerPhone` AS `customerPhone`,
	`cmp`.`customerName` AS `customerName`,
	`ktot`.`customerId` as `customerId`,
	`ktot`.`numberOfOrders` AS `numberOfOrders`,
	`ktot`.`latest_kto_id` AS `latest_kto_id`,
	`cmp`.`lastMsg` AS `lastMsg`,
	`cmp`.`hiddenFlag` AS `hiddenFlag`,
	`cmp`.`totalIncoming` AS `totalIncoming`,
	`cmp`.`totalOutGoing` AS `totalOutGoing`,
	`user`.`id` as `userId`,
	CONCAT_WS(' ', `user`.`firstName`, `user`.`lastName`) AS `claimedBy`,
	`cc`.`createdAt` AS `claimedAt`
FROM `%(db)s`.`customer_msg_phone` AS `cmp`
LEFT JOIN (
	SELECT `cmp1`.`id` AS `id`, COUNT(0) AS `numberOfOrders`,
			MAX(`kto`.`id`) AS `latest_kto_id`, `kto`.`customerId`
	FROM `%(db)s`.`customer_msg_phone` `cmp1`
	JOIN `%(db)s`.`kt_order` AS `kto` ON (
		`cmp1`.`customerPhone` = SUBSTR(`kto`.`phoneNumber`, -(10))
		AND ((`kto`.`cardType` <> 'TESTCARD')
		OR ISNULL(`kto`.`cardType`))
	)
	GROUP BY `cmp1`.`id`
) `ktot` ON `ktot`.`id` = `cmp`.`id`
LEFT JOIN `%(db)s`.`customer_claimed` as `cc` ON `cc`.`phoneNumber` = `cmp`.`customerPhone`
LEFT JOIN `%(db)s`.`user`  ON `user`.`id` = `cc`.`user`
WHERE %(where)s
