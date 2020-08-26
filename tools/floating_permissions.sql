SELECT `p`.`_id` as `_id`,
		`u`.`_id` as `user`,
		`a`.`_id` as `agent`,
		`pp`.`_id` as `patient`
FROM `mems`.`auth_permission` as `p`
LEFT JOIN `mems`.`auth_user` as `u` ON `p`.`user` = `u`.`_id`
LEFT JOIN `mems`.`csr_agent` as `a` ON `p`.`user` = `a`.`_id`
LEFT JOIN `mems`.`patient_account` `pp` ON `p`.`user` = `pp`.`_id`
WHERE `u`.`_id` IS NULL
AND `a`.`_id` IS NULL
AND `pp`.`_id` IS NULL
