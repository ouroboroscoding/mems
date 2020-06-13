SELECT
	`smp`.`action`,
	`smp`.`note`,
	`smp`.`createdAt`,
	CONCAT(`user`.`firstName`, ' ', `user`.`lastName`) AS `createdBy`,
	`user`.`userRole` AS `userRole`
FROM
	`%(db)s`.`kt_order` as `kto`,
	`%(db)s`.`%(table)s` as `smp`,
	`%(db)s`.`user` as `user`
WHERE
	`kto`.`customerId` = %(id)d AND
	`smp`.`parentTable` = 'kt_order' AND
	`smp`.`parentColumn` = 'orderId' AND
	`smp`.`columnValue` = `kto`.`orderId` AND
	`smp`.`createdBy` = `user`.`id`

UNION

SELECT
	`smp`.`action`,
	`smp`.`note`,
	`smp`.`createdAt`,
	CONCAT(`user`.`firstName`, ' ', `user`.`lastName`) AS `createdBy`,
	`user`.`userRole` AS `userRole`
FROM
	`%(db)s`.`%(table)s` as `smp`,
	`%(db)s`.`user` as `user`
WHERE
	`smp`.`parentTable` = 'kt_customer' AND
	`smp`.`parentColumn` = 'customerId' AND
	`smp`.`columnValue` = %(id)d AND
	`smp`.`createdBy` = `user`.`id`

ORDER BY `createdAt`
