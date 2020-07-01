SELECT
	`fromPhone`, count(`fromPhone`) as `count`
FROM
	`%(db)s`.`%(table)s`
WHERE
	`createdAt` > FROM_UNIXTIME(%(ts)d) AND
	`fromPhone` IN (%(numbers)s)
GROUP BY
	`fromPhone`
