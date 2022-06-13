"""
This script calls all other scripts in order. You can step through it as needed.
"""

#%%
import os
import datetime
import subprocess

def run_task(task_name: str, script: str):

    start_time = datetime.datetime.now()

    print("\n\n--------------------------------------")
    print(task_name)
    print("--------------------------------------\n")

    if script.lower().endswith(".r"):

        output = subprocess.check_output(
            ["rscript", os.path.join("src", script)],
            # We're in /src, R expects us to be in project root
            cwd=os.path.join(os.path.dirname(__file__), ".."))

        print(output.decode("UTF-8"))

    elif script.lower().endswith(".py"):

        # Replace / with . because we're importing them as modules
        __import__(script.lower().replace('.py', '').replace("/", "."))

    else:
        raise Exception("Unrecognized script format.")

    print(f"Elapsed time: {(datetime.datetime.now() - start_time).total_seconds() / 60:.2f} minutes")


#%% #####################################
# Downloaders
#########################################

# Download all labeled data (1 min total)
files = os.listdir("downloaders/states")
files = [f for f in files if f.lower().endswith("_wsb.r")]
for f in files:
    run_task(
        f"Downloading {f[9:11].upper()}",
        "downloaders/states/" + f)

#%%
# Download ECHO (30 secs)
run_task(
    "Downloading ECHO admin data",
    "downloaders/download_echo.R")

#%%
# Download FRS (1.5 mins)
run_task(
    "Downloading FRS centroids", 
    "downloaders/download_frs.R")

#%%
# Download MHP (10 secs)
run_task(
    "Downloading mobile home parks point data", 
    "downloaders/download_mhp.R")

#%%
# Download SDWIS (5 mins)
run_task(
    "Downloading SDWIS data", 
    "downloaders/download_sdwis.py")

#%%
# Download TIGER (3 mins)
run_task(
    "Downloading TIGRIS places and Natural Earth coastline", 
    "downloaders/download_tigris_ne.R")

#%%
# Download UCMR (10 secs)
run_task(
    "Downloading UCMR occurrence data", 
    "downloaders/download_ucmr.R")


#%% #####################################
# Transformers
#########################################

# Transform Labeled States (~3 min total)
files = os.listdir("transformers/states")
files = [f for f in files if f.lower().endswith(".r")]
for f in files:
    run_task(
        f"Transforming {f[14:16].upper()}",
        "transformers/states/" + f)

# Combine labeled states
run_task(
    f"Combine labeled states",
    "transformers/combine_transformed_wsb.R")

#%%
# Transform ECHO (30 mins due to geojson save...might need refactor)
run_task(
    "Transforming ECHO data",
    "transformers/transform_echo.R")

#%%
# Transform FRS (3 mins)
run_task(
    "Transforming FRS centroids",
    "transformers/transform_frs.R")

#%%
# Transform MHP (30 secs)
run_task(
    "Transforming mobile home parks point data",
    "transformers/transform_mhp.R")

#%%
# Transform SDWIS (1 min)
run_task(
    "Transforming SDWIS Water Systems",
    "transformers/transform_sdwis_ws.py")

run_task(
    "Transforming SDWIS Water Service Areas",
    "transformers/transform_sdwis_service.py")

run_task(
    "Transforming SDWIS Geographic Areas",
    "transformers/transform_sdwis_geo_areas.py")

# We didn't end up using this data
# run_task(
#     "Transforming SDWIS Water System Facilities",
#     "transformers/transform_sdwis_wsf.py")


#%%
# Transform TIGER (1 min)
run_task(
    "Transforming TIGRIS places and Natural Earth coastline",
    "transformers/transform_tigris_ne.R")

#%%
# Transform UCMR (13 mins)
run_task(
    "Transforming UCMR occurrence data",
    "transformers/transform_ucmr.R")


#%% ###############################
# Match
###################################

# Mappings (5 min)
run_task(
    "Mapping data to postgres",
    "match/1-mappings.py")

#%%
# Matching (1 min)
run_task(
    "Running match algorithms",
    "match/2-matching.py")

#%%
# Superjoin & Output (40 secs)
run_task(
    "Running superjoin",
    "match/3-superjoin.py")


#%% ###############################
# Model
###################################

# Preprocessing (45 secs)
run_task(
    "Preprocessing data for model",
    "model/01_preprocess.R")

#%%
# Linear model (2 mins)
run_task(
    "Running linear model for wsb estimation",
    "model/02_linear.R")


#%% ###############################
# Combine
###################################

# Combine tiers (2 mins)
run_task(
    "Combining tiers into one spatial wsb layer",
    "combine_tiers.py")
