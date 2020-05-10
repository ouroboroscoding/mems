SELECT
	`fromPhone`,
	`toPhone`,
	`type`
FROM
	`%(db)s`.`%(table)s`
WHERE
	`createdAt` > FROM_UNIXTIME(%(ts)d) AND (
		`fromPhone` IN (%(numbers)s) OR
		`toPhone` IN (%(numbers)s)
	)
