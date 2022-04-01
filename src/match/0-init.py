"""
This scripts simply sets up the database.
"""
#%%

import os
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv()

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])

#%%

# Read in the SQL and execute against the database
this_folder = os.path.dirname(__file__)

with open(this_folder + "/init_model.sql") as file:
    sql = file.read()

conn.execute(sql)