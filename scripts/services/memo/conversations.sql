SELECT
    `cmp`.`id` AS `id`,
    `cmp`.`customerPhone` AS `customerPhone`,
    `cmp`.`customerName` AS `customerName`,
    `ktot`.`customerId` as `customerId`,
    `ktot`.`numberOfOrders` AS `numberOfOrders`,
    `ktot`.`latest_kto_id` AS `latest_kto_id`,
    `cmp`.`lastMsg` AS `lastMsg`,
    `cmp`.`lastMsgDir` AS `lastMsgDir`,
    `cmp`.`lastMsgAt` AS `lastMsgAt`,
    `cmp`.`hiddenFlag` AS `hiddenFlag`,
    `cmp`.`totalIncoming` AS `totalIncoming`,
    `cmp`.`totalOutGoing` AS `totalOutGoing`,
    `cmp`.`lastViewedBy` AS `lastViewedBy`,
    CONCAT(`user`.`firstName`, ' ', `user`.`lastName`) AS `lastViewedByName`,
    `cmp`.`lastViewedAt` AS `lastViewedAt`
FROM `customer_msg_phone` `cmp`
LEFT JOIN `user` ON `user`.`id` = `cmp`.`lastViewedBy`
LEFT JOIN (
    SELECT `cmp1`.`id` AS `id`, COUNT(0) AS `numberOfOrders`,
            MAX(`kto`.`id`) AS `latest_kto_id`, `kto`.`customerId`
    FROM `customer_msg_phone` `cmp1`
    JOIN `kt_order` `kto` ON (
        `cmp1`.`customerPhone` = SUBSTR(`kto`.`phoneNumber`, -(10))
        AND ((`kto`.`cardType` <> 'TESTCARD')
        OR ISNULL(`kto`.`cardType`))
    )
    GROUP BY `cmp1`.`id`
) `ktot` ON `ktot`.`id` = `cmp`.`id`
WHERE `numberOfOrders` > 0
AND `hiddenFlag` = 'N'
AND `lastMsgDir` = 'Incoming'
