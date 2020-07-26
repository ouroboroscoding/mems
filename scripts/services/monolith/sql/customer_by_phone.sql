SELECT
	`ktc`.`customerId` as `customerId`,
	`cc`.`user` as `claimedUser`
FROM `%(db)s`.`%(table)s` as `ktc`
LEFT JOIN `%(db)s`.`customer_claimed` as `cc` ON `ktc`.`phoneNumber` = `cc`.`phoneNumber`
WHERE `ktc`.`phoneNumber` IN ('%(number)s', '1%(number)s')
ORDER BY `ktc`.`updatedAt` DESC
LIMIT 1
