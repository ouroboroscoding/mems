SELECT `customerId`, COUNT(*) as `count`
FROM (
	SELECT
		`kto`.`customerId` as `customerId`,
		`smp`.`id` as `id`
	FROM
		`%(db)s`.`kt_order` as `kto`,
		`%(db)s`.`%(table)s` as `smp`
	WHERE
		`kto`.`customerId` IN (%(ids)s) AND
		`smp`.`parentTable` = 'kt_order' AND
		`smp`.`parentColumn` = 'orderId' AND
		`smp`.`columnValue` = `kto`.`orderId` AND
		`smp`.`createdAt` > FROM_UNIXTIME(%(ts)d)

	UNION

	SELECT
		`smp`.`columnValue` as `customerId`,
		`smp`.`id` as `id`
	FROM
		`%(db)s`.`%(table)s` as `smp`
	WHERE
		`smp`.`parentTable` = 'kt_customer' AND
		`smp`.`parentColumn` = 'customerId' AND
		`smp`.`columnValue` IN (%(ids)s) AND
		`smp`.`createdAt` > FROM_UNIXTIME(%(ts)d)
) as `t`
GROUP BY `t`.`customerId`
