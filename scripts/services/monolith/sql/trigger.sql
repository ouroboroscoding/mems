SELECT
	`wdt`.`customerId` as `customerId`,
	`wdt`.`triggered` as `triggered`,
	`wdt`.`opened` as `opened`,
	`wdt`.`shipped` as `shipped`,
	`wdo`.`queue` as `outreachQueue`,
	`wdo`.`reason` as `outreachReason`,
	`wde`.`memberSince` as `eligSince`,
	`wde`.`memberThru` as `eligThru`
FROM `%(db)s`.`%(table)s` as `wdt`
LEFT JOIN `%(db)s`.`wd_outreach` as `wdo` ON `wdt`.`customerId` = `wdo`.`customerId`
LEFT JOIN `%(db)s`.`wd_eligibility` as `wde` on `wdt`.`customerId` = `wde`.`customerId`
WHERE `wdt`.`customerId` = '%(customerId)s'
