SELECT
	`cmp`.`customerPhone`,
	`cmp`.`customerName`,
	`cc`.`transferredBy`
FROM
	`%(db)s`.`customer_msg_phone` AS `cmp` JOIN
	`%(db)s`.`customer_claimed` as `cc` ON
		`cmp`.`customerPhone` = `cc`.`phoneNumber`
WHERE
	`cc`.`user` = %(user)d
ORDER BY
	`cc`.`transferredBy` DESC
