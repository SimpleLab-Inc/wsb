#%%

import os
from shapely.geometry import Polygon
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
import match.helpers as helpers

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]

#%% ##########################################
# SDWIS
##############################################

"""
# SDWIS Schema

Table relationships:
- water_system
- water_system : water_system_facility is 1 : 0/N (~300 pwsid's missing, N=9.8 mean (wow!))
- water_system : service_area is 1 : 0/N, but almost 1:N (~1k pwsid's missing, N=1.2 mean)
- water_system : geographic_area is 1 : 0/1, but almost 1:1 (~1k pwsid's missing)

Here are the useful columns we want from SDWIS and supplemental tables
ws.pwsid - the PK
ws.pws_name - name
ws.pws_activity_code - active or not
ws.pws_type_code - Filtered to "cws" only so maybe we don't need it
ws.address_line1 - "The address applicable to the legal entity", whatever that means
ws.address_line2
ws.city_name
ws.zip_code
ws.primacy_agency_code
wsf.facility_id - Optional. This denormalizes the data substantially.
sa.service_area_type_code - for municipal vs mobile home park
ga.city_served - this column is not populated in ws unfortunately
ga.county_served - Maybe this will be helpful?
"""

#########
# 1) SDWIS water_systems - PWSID is unique
keep_columns = ["pwsid", "pws_name", "primacy_agency_code", 
    "address_line1", "address_line2", "city_name", "zip_code", "state_code",
    "population_served_count", "service_connections_count", "owner_type_code",
    "primacy_type", "is_wholesaler_ind", "primary_source_code"]

sdwis = pd.read_csv(
    os.path.join(DATA_PATH, "sdwis_water_system.csv"),
    usecols=keep_columns,
    dtype="string")

pwsids = helpers.get_pwsids_of_interest()

sdwis = sdwis.loc[sdwis["pwsid"].isin(pwsids)]

# If state_code is NA, copy from primacy_agency_code
mask = sdwis["state_code"].isna()
sdwis.loc[mask, "state_code"] = sdwis.loc[mask, "primacy_agency_code"]


#########
# Supplement with geographic_area

# geographic_area - PWSID is unique, very nearly 1:1 with water_system
# ~1k PWSID's appear in water_system but not geographic_area
# We're trying to get city_served and county_served, but these columns aren't always populated
sdwis_ga = pd.read_csv(
    os.path.join(DATA_PATH, "sdwis_geographic_area.csv"),
    usecols=["pwsid", "city_served", "county_served"],
    dtype="string")

# Verify: pwsid is unique
if not sdwis_ga["pwsid"].is_unique:
    raise Exception("Failed assumption: pwsid in geographic_area is assumed to be unique")

sdwis = sdwis.merge(sdwis_ga, on="pwsid", how="left")

#########
# Supplement with service_area

# This is N:1 with sdwis, which is annoying
# (each pws has on average 1.2 service_area_type_codes)

# service_area - PWSID + service_area_type_code is unique
# ~1k PWSID's appear in water_system but not service_area
sdwis_sa = pd.read_csv(
    os.path.join(DATA_PATH, "sdwis_service_area.csv"),
    usecols=["pwsid", "service_area_type_code"])

# Filter to the pws's we're interested in
sdwis_sa = sdwis_sa.loc[sdwis_sa["pwsid"].isin(sdwis["pwsid"])]

# Supplement sdwis. I'll group it into a python list to avoid denormalized
# Could also do a comma-delimited string. We'll see what seems more useful in practice.
sdwis_sa = sdwis_sa.groupby("pwsid")["service_area_type_code"].apply(list)

sdwis = sdwis.merge(sdwis_sa, on="pwsid", how="left")

# Verification
if not sdwis["pwsid"].is_unique:
    raise Exception("Expected sdwis pwsid to be unique")

sdwis.head()

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id     = sdwis["pwsid"],
    source_system        = "sdwis",
    contributor_id       = "sdwis." + sdwis["pwsid"],
    master_key           = sdwis["pwsid"],
    pwsid                = sdwis["pwsid"],
    state                = sdwis["state_code"],
    name                 = sdwis["pws_name"],
    address_line_1       = sdwis["address_line1"],
    address_line_2       = sdwis["address_line2"],
    city                 = sdwis["city_name"],
    zip                  = sdwis["zip_code"],
    county               = sdwis["county_served"],
    city_served          = sdwis["city_served"],
    geometry             = Polygon([]),                     # Empty geometry.
    primacy_agency_code        = sdwis["primacy_agency_code"],
    primacy_type               = sdwis["primacy_type"],
    population_served_count    = sdwis["population_served_count"],
    service_connections_count  = sdwis["service_connections_count"].astype("float").astype("int"),
    owner_type_code            = sdwis["owner_type_code"],
    service_area_type_code     = sdwis["service_area_type_code"].astype("str"),
    is_wholesaler_ind          = sdwis["is_wholesaler_ind"],
    primary_source_code        = sdwis["primary_source_code"],
)

df = df.set_crs(epsg=EPSG, allow_override=True)

#%%
helpers.load_to_postgis("sdwis", df)