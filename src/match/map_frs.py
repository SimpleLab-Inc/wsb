#%%

import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

import match.helpers as helpers

load_dotenv()

pd.options.display.max_columns = None

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]


#%%

frs = gpd.read_file(os.path.join(DATA_PATH, "frs.gpkg"))
print("Read FRS file.")

pwsids = helpers.get_pwsids_of_interest()
print("Retrieved PWSID's of interest.")

# Bring in echo so that we can compare FRS and avoid duplication
echo = pd.read_csv(DATA_PATH + "/echo.csv", dtype="str",
    usecols=["pwsid", "fac_name", "fac_lat", "fac_long"])

print("Read ECHO (to avoid duplication)")

# Filter to those in SDWIS
# And only those with interest_type "WATER TREATMENT PLANT". Other interest types are already in Echo.
frs = frs[
    frs["pwsid"].isin(pwsids) &
    (frs["interest_type"] == "WATER TREATMENT PLANT")]

# We only need a subset of the columns
keep_columns = [
    "registry_id", "pwsid", "state_code", "primary_name", "location_address",
    "city_name", "postal_code", "county_name",
    "latitude83", "longitude83", "geometry", "ref_point_desc",
    "collect_mth_desc"]

frs = frs[keep_columns]

# Exclude FRS that are identical to echo on name and lat/long.
# Maybe later, we also want to allow them through if they have different addresses.
frs = frs.loc[frs
    # Find matches to echo, then only include those from FRS that _didn't_ match
    .reset_index()
    .merge(echo,
        left_on=["pwsid", "primary_name", "latitude83", "longitude83"],
        right_on=["pwsid", "fac_name", "fac_lat", "fac_long"],
        how="outer", indicator=True)
    .query("_merge == 'left_only'")
    ["index"]
]
print("Filtered FRS")

# Furthermore, drop entries where all the columns of interest are duplicated
frs = frs.drop_duplicates(subset=list(set(frs.columns) - set("registry_id")), keep="first")

print(f"{len(frs)} FRS entries remain after removing various duplicates")

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id        = frs["pwsid"],
    source_system           = "frs",
    contributor_id          = "frs." + frs["registry_id"] + "." + frs["pwsid"], # Apparently neither registry_id nor pwsid is fully unique, but together they are
    master_key              = frs["pwsid"],
    pwsid                   = frs["pwsid"],
    state                   = frs["state_code"],
    name                    = frs["primary_name"],
    address_line_1          = frs["location_address"],
    city                    = frs["city_name"],
    zip                     = frs["postal_code"],
    county                  = frs["county_name"],
    primacy_agency_code     = frs["pwsid"].str[0:2],
    centroid_lat            = frs["latitude83"],
    centroid_lon            = frs["longitude83"],
    geometry                = frs["geometry"],
    centroid_quality        = frs["ref_point_desc"],
    data_source             = frs["collect_mth_desc"]
)

# Some light cleansing
df["zip"] = df["zip"].str[0:5]

# %%
helpers.load_to_postgis("frs", df)
