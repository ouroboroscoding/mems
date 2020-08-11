SELECT
	`id`,
	`status`,
	`errorMessage` as `error`,
	`fromName`,
	`notes`,
	`createdAt`,
	`type`
FROM
	`%(db)s`.`%(table)s`
WHERE
	`fromPhone` IN ('%(number)s', '1%(number)s') OR
	`toPhone` IN ('%(number)s', '1%(number)s')
ORDER BY
	`createdAt` ASC
