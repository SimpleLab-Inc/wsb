#%%

import os
from typing import List, Optional
import numpy as np
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()

STAGING_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]
PROJ = os.environ["WSB_EPSG_AW"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])

class MatchScorer:

    def __init__(self):
        self.boundary_df = (self.get_data("tiger", ["contributor_id", "geometry"])
            .set_index("contributor_id"))

        self.labeled_df = self.get_data("labeled", ["pwsid", "master_key", "geometry"])

    def score_tiger_matches(self, matches: pd.DataFrame, proximity_buffer: int = 1000) -> pd.DataFrame:

        """
        Given a set of matches to boundary data, compare it to known geometries
        (labeled data) to evaluate whether each match is good or bad. This can
        be used to evaluate the effectiveness of our matching.

        The match DF should have columns: master_key, candidate_contributor_id
        """

        # Extract a series of "known geometries" from the labeled geometry data
        known_geometries = gpd.GeoSeries(
            self.labeled_df[["pwsid", "geometry"]]
            .merge(matches[["master_key", "candidate_contributor_id"]], left_on="pwsid", right_on="master_key")
            .set_index(["pwsid", "candidate_contributor_id"])
            ["geometry"])

        # Extract a series of "potential geometries" from the matched boundary data
        candidate_matches = gpd.GeoDataFrame(matches
            .join(self.boundary_df["geometry"], on="candidate_contributor_id")
            .rename(columns={"master_key": "pwsid"})
            .set_index(["pwsid", "candidate_contributor_id"])
            [["geometry"]])

        # Filter to only the PWS's that appear in both series
        # 7,423 match
        known_geometries = (known_geometries
            .loc[known_geometries.index.isin(candidate_matches.index)]
            .sort_index())

        candidate_matches = (candidate_matches
            .loc[candidate_matches.index.isin(known_geometries.index)]
            .sort_index())

        print("Retrieved and aligned data.")

        # Switch to a projected CRS
        known_geometries = known_geometries.to_crs(PROJ)
        candidate_matches = candidate_matches.to_crs(PROJ)

        print("Converted to a projected CRS.")

        distances = known_geometries.distance(candidate_matches, align=True)
        print("Calculated distances.")

        # A few empty labeled geometries cause NA distances. Filter only non-NA
        distances = distances[distances.notna()]
        distances.name = "distance"

        # re-join to the match table
        candidate_matches = candidate_matches.join(distances, on=["pwsid", "candidate_contributor_id"], how="inner")

        # Assign a score - 1 if a good match, 0 if not a good match
        candidate_matches["score"] = candidate_matches["distance"] <= proximity_buffer

        print("Assigned scores.")

        return candidate_matches

    def get_data(self, system: str, columns: List[str] = ["*"]) -> pd.DataFrame:
        print(f"Pulling {system} data from database...", end="")

        df = gpd.GeoDataFrame.from_postgis(f"""
                SELECT {", ".join(columns)}
                FROM pws_contributors
                WHERE source_system = '{system}';""",
            conn, geom_col="geometry")

        print("done.")

        return df