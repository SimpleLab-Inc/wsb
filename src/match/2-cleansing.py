#%%
import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv()

pd.options.display.max_columns = None

EPSG = os.environ["WSB_EPSG"]
PROJ = os.environ["WSB_EPSG_AW"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])


def _run_cleanse_rule(conn, rule_name: str, sql: str):
    result = conn.execute(sql)
    print(f"Ran cleanse rule '{rule_name}': {result.rowcount} rows affected")

#%%
# First apply a bunch of SQL cleanses

PO_BOX_REGEX = r'^P[\. ]?O\M\.? *BOX +\d+$'

# Upper-case columns
for col in [
        "name", "address_line_1", "address_line_2", "city", "state",
        "county", "city_served", "centroid_quality"
    ]:
    _run_cleanse_rule(conn,
        f"Upper-case {col}",
        f"""
            UPDATE pws_contributors
            SET {col} = UPPER({col})
            WHERE
                {col} ~ '[a-z]';
        """)

_run_cleanse_rule(conn,
    "NULL out nonexistent zip code '99999'",
    f"""
        UPDATE pws_contributors
        SET zip = NULL
        WHERE
            zip = '99999';
    """)

_run_cleanse_rule(conn,
    "Remove PO BOX from address_line_1",
    f"""
        UPDATE pws_contributors
        SET
            address_quality = 'PO BOX',
            address_line_1 = NULL
        WHERE
            address_line_1 ~ '{PO_BOX_REGEX}';
    """)

_run_cleanse_rule(conn,
    "Remove PO BOX from address_line_2",
    f"""
    UPDATE pws_contributors
    SET
        address_quality = 'PO BOX',
        address_line_2 = NULL
    WHERE
        address_line_2 ~ '{PO_BOX_REGEX}';
    """)

_run_cleanse_rule(conn,
    "If there's an address in line 2 but not line 1, move it",
    f"""
        UPDATE pws_contributors
        SET
            address_line_1 = address_line_2,
            address_line_2 = NULL
        WHERE
            (address_line_1 IS NULL OR address_line_1 = '') AND
            address_line_2 IS NOT NULL;
    """)

_run_cleanse_rule(conn,
    "Standardize geometry quality",
    f"""
        UPDATE pws_contributors
        SET centroid_quality = 'ZIP CODE CENTROID'
        WHERE
            centroid_quality = 'ZIP CODE-CENTROID';
    """)

#%%
#####################
# Handle Impostors
#####################

print("Checking for impostors...")

# Pull data from the DB
df = gpd.GeoDataFrame.from_postgis("""
        SELECT
            contributor_id,
            source_system,
            state,
            primacy_agency_code,
            geometry
        FROM pws_contributors
        WHERE
            source_system IN ('echo', 'frs') AND
            geometry IS NOT NULL AND
            NOT st_isempty(geometry)
    """, conn, geom_col="geometry"
    ).set_index("contributor_id")

# Convert to projected
df = df.to_crs(PROJ)

# How many entries where primacy_agency_code differs from primacy_agency? 738
# How many entries where primacy_agency_code is numeric? 379
# Entries where state is numeric? 0
# Entries where state is null? 0

# In cases where primacy_agency_code is numeric, sub in the state
mask = df["primacy_agency_code"].str.contains(r"\d\d", regex=True)
df.loc[mask, "primacy_agency_code"] = df.loc[mask]["state"]

#%%

# Read in state boundaries and convert to projected CRS
states = (gpd
    .read_file("../layers/us_states.geojson")
    [["stusps", "geometry"]]
    .rename(columns={"stusps": "state"})
    .set_index("state")
    .to_crs(PROJ))

#%%

# Series 1 is pwsid + geometry
s1 = df["geometry"]

# Series 2 is generic state bounds joined to each pwsid on primacy_agency_code
s2 = (df
    .drop(columns="geometry")
    .join(states, on="primacy_agency_code")
    ["geometry"])

# Calculate the distance between the supplied boundary and the expected state
distances = s1.distance(s2, align=True)

# Any that are >50 kilometers are impostors
impostors = (df
    .loc[distances[(distances > 50_000)].index]
    .to_crs("epsg:" + EPSG)
    .reset_index())

print(f"Found {len(impostors)} impostors.")

#%%
# Save to the database
impostors.to_postgis("impostors", conn, if_exists="replace")

#%%
# Remove the address, lat/lon, and geometry when it's an "impostor"
conn.execute("""
        UPDATE pws_contributors
        SET
            address_line_1  = NULL,
            address_line_2  = NULL,
            city            = NULL,
            state           = NULL,
            zip             = NULL,
            geometry        = 'GEOMETRYCOLLECTION EMPTY',
            centroid_lat    = NULL,
            centroid_lon    = NULL
        WHERE
            contributor_id IN (SELECT contributor_id FROM impostors);
    """, conn)

print("Null'd out impostor addresses and lat/lon.")