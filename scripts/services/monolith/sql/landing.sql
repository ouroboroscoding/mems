SELECT `t`.`landing_id`, `t`.`formId`, `t`.`submitted_at`, `complete`
FROM `%(db)s`.`%(table)s` as `t`
WHERE `lastName` = '%(lastName)s'
AND `birthDay` IS NOT NULL
AND `birthDay` != ''
AND (
	`email` = '%(email)s' OR
	`phone` IN ('1%(phone)s', '%(phone)s')
)
ORDER BY `submitted_at` DESC
