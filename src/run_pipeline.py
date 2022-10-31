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

#%%
# Download Contributed PWS (10 secs)
run_task(
    "Downloading contributed pws boundaries",
    "downloaders/download_contributed_pws.R")


#%% #####################################
# Transformers
#########################################

# Transform Labeled States (~3 min total)
files = os.listdir("transformers/states")
failures = []
for f in files:
    try:
        run_task(
            f"Transforming {f[14:16].upper()}",
            "transformers/states/" + f)
    except Exception as e:
        failures.append(f)

print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!")
print("Warning: Some state transformers failed to run!")
print("Failed: " + ", ".join(failures))
print("!!!!!!!!!!!!!!!!!!!!!!!!!!")

# Combine labeled states
run_task(
    f"Combine labeled states",
    "transformers/combine_transformed_wsb.R")

# Transform contributed pws
run_task(
    "Transforming contribtued pws",
    "transformers/transform_contributed_pws.R")

#%%
# Transform ECHO (3m30s)
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

# Mappings (5 min total)
run_task(
    "Mapping sdwis data to postgres",
    "match/map_sdwis.py")

run_task(
    "Mapping frs data to postgres",
    "match/map_frs.py")

run_task(
    "Mapping echo data to postgres",
    "match/map_echo.py")

run_task(
    "Mapping mhp data to postgres",
    "match/map_mhp.py")

run_task(
    "Mapping tiger data to postgres",
    "match/map_tiger.py")

run_task(
    "Mapping ucmr data to postgres",
    "match/map_ucmr.py")

run_task(
    "Mapping labeled data to postgres",
    "match/map_labeled.py")

run_task(
    "Mapping contributed data to postgres",
    "match/map_contributed.py")

#%%
# Clean the data (20 secs)
run_task(
    "Cleansing the data",
    "match/2-cleansing.py")

#%%
# Matching Tiger and MHP (1 min)
run_task(
    "Running match algorithms",
    "match/3-matching.py")

#%%
# Selecting best TIGER matches (20 secs)
run_task(
    "Finding best boundary matches",
    "match/4-rank_boundary_matches.py")

#%%
# Find best centroids for "modeled" system (20 secs)
run_task(
    "Finding best centroids",
    "match/5-select_modeled_centroids.py")


#%% ###############################
# Model
###################################

# Preprocessing (10 secs)
run_task(
    "Preprocessing data for model",
    "model/01_preprocess.R")

#%%
# Linear model (40 secs)
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
