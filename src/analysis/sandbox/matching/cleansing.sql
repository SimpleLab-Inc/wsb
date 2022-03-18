-- SQL script to quickly cleanse the entire XREF table


-- Cleansing
UPDATE utility_xref SET zip = NULL WHERE zip = '99999';

-- Any that have "PO BOX" are admin and should be removed
UPDATE utility_xref
SET
    address_quality = 'PO BOX',
    address_line_1 = NULL
WHERE
    address_line_1 ~ '^P[\. ]?O\M\.? *BOX +\d+$';

UPDATE utility_xref
SET
    address_quality = 'PO BOX',
    address_line_2 = NULL
WHERE
    address_line_2 ~ '^P[\. ]?O\M\.? *BOX +\d+$';

-- If there's an address in line 2 but not line 1, move it
UPDATE utility_xref
SET
    address_line_1 = address_line_2,
    address_line_2 = NULL
WHERE
    (address_line_1 IS NULL OR address_line_1 = '') AND
    address_line_2 IS NOT NULL;