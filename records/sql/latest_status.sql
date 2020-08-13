SELECT
	`kto`.`orderId`,
	`sos`.`attentionRole`,
	`sos`.`orderLabel`
FROM `%(db)s`.`kt_order` as `kto`
LEFT JOIN `%(db)s`.`%(table)s` as `sos`
	ON `kto`.`orderId` = `sos`.`orderId`
WHERE `kto`.`customerId` = %(customerId)d
ORDER BY `kto`.`createdAt` DESC
LIMIT 1
