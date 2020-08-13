SELECT
	`cmp`.`customerPhone`,
	`cmp`.`customerName`
FROM
	`%(db)s`.`customer_msg_phone` AS `cmp` JOIN
	`%(db)s`.`customer_claimed` as `cc` ON
		`cmp`.`customerPhone` = `cc`.`phoneNumber`
WHERE
	`cc`.`user` = %(user)d
