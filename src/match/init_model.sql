DROP TABLE IF EXISTS pws_contributors;

CREATE TABLE pws_contributors (
    contributor_id      TEXT NOT NULL PRIMARY KEY,
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
    primacy_type        TEXT,
    population_served_count   INT,
    service_connections_count INT,
    owner_type_code           CHAR(1),
    service_area_type_code    TEXT,
    is_wholesaler_ind         BOOLEAN,
    primary_source_code       TEXT,
    geometry_lat        DECIMAL(10, 8),
    geometry_long       DECIMAL(11, 8),
    geometry            GEOMETRY(GEOMETRY, 4326),
    geometry_quality    TEXT
);

CREATE INDEX ix__pws_contributors__source_system ON pws_contributors (source_system);
CREATE INDEX ix__pws_contributors__source_system_id ON pws_contributors (source_system_id);
CREATE INDEX ix__pws_contributors__master_key ON pws_contributors (master_key);