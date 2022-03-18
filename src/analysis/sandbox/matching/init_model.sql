DROP TABLE IF EXISTS utility_xref;

CREATE TABLE utility_xref (
    xref_id             TEXT NOT NULL PRIMARY KEY,
    source_system       TEXT NOT NULL,
    source_system_id    TEXT NOT NULL,
    master_key          TEXT NOT NULL,
    pwsid               TEXT,
    name                TEXT,
    address_line_1      TEXT,
    address_line_2      TEXT,
    city                TEXT,
    state               CHAR(2),
    zip                 CHAR(5),
    county              TEXT,
    address_quality     TEXT,
    city_served         TEXT,
    primacy_agency_code TEXT,
    geometry_lat        DECIMAL(10, 8),
    geometry_long       DECIMAL(11, 8),
    geometry            GEOMETRY(GEOMETRY, 4326),
    geometry_quality    TEXT
);

CREATE INDEX ix__utility_xref__source_system ON utility_xref (source_system)
CREATE INDEX ix__utility_xref__source_system_id ON utility_xref (source_system_id)
CREATE INDEX ix__utility_xref__master_key ON utility_xref (master_key)

-- Clone the xref table to the "raw" table
CREATE TABLE utility_raw AS TABLE utility_xref;