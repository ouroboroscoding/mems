SELECT `p`.`_id` as `_id`,
		`u`.`_id` as `user`,
		`a`.`_id` as `agent`,
		`pp`.`_id` as `patient`,
		`mp`.`_id` as `provider`
FROM `mems`.`auth_permission` as `p`
LEFT JOIN `mems`.`auth_user` as `u` ON `p`.`user` = `u`.`_id`
LEFT JOIN `mems`.`csr_agent` as `a` ON `p`.`user` = `a`.`_id`
LEFT JOIN `mems`.`patient_account` as `pp` ON `p`.`user` = `pp`.`_id`
LEFT JOIN `mems`.`providers_provider` as `mp` ON `p`.`user` = `mp`.`_id`
WHERE `u`.`_id` IS NULL
AND `a`.`_id` IS NULL
AND `pp`.`_id` IS NULL
AND `mp`.`_id` IS NULL
