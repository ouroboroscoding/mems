SELECT
	`fromName`,
	`notes`,
	`createdAt`,
	`type`
FROM
	`%(db)s`.`%(table)s`
WHERE
	`fromPhone` = %(number)s OR
	`toPhone` = %(number)s
ORDER BY
	`createdAt` ASC
