SELECT
	`smp`.`action`,
	`smp`.`note`,
	`smp`.`createdAt`,
	CONCAT(`user`.`firstName`, ' ', `user`.`lastName`) AS `createdBy`,
	`user`.`userRole` AS `userRole`
FROM `%(db)s`.`kt_customer` as `ktc`
JOIN `%(db)s`.`kt_order` as `kto` ON `ktc`.`customerId` = `kto`.`customerId`
JOIN `%(db)s`.`%(table)s` as `smp` ON `kto`.`orderId` = `smp`.`columnValue`
JOIN `%(db)s`.`user` as `user` ON `smp`.`createdBy` = `user`.`id`
WHERE
	`ktc`.`customerId` = %(id)d AND
	`smp`.`parentTable` = 'kt_order' AND
	`smp`.`parentColumn` = 'orderId'
ORDER BY `createdAt` DESC
