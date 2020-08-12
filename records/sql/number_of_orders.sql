SELECT
	`orderId`
FROM
	`%(db)s`.`%(table)s` as `kto`
WHERE
	`kto`.`phoneNumber` IN('%(phone)s', '1%(phone)s')
	AND (`kto`.`cardType` <> 'TESTCARD'
	OR ISNULL(`kto`.`cardType`))
