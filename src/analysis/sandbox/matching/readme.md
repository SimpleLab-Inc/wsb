# Environment Setup

## Start a PostGIS Docker container

`docker run -e POSTGRES_PASSWORD=postgres -d --name postgis -p 5433:5432 -v postgis_volume:/var/lib/postgresql/data postgis/postgis`

Notes about this command:
- The database password will be "postgres". This is safe when run locally, but never use this on a server exposed to the internet.
- PostGIS will be available on port 5433
- The data will be stored in a named docker volume called `postgres_volume`. This will preserve your data even if the container is stopped and removed.

### Configure the database

Log into the container:

`docker exec -it postgis bash`

Connect to the PostGIS server using psql:

`psql -U postgres`

Create a new database:

`create database wsb;`

Connect to the database:

`\c wsb`

Add the PostGIS extension:

`CREATE EXTENSION postgis;`

Exit out of psql:

`exit`

Exit out of the docker container:

`exit`

# Initialize the database

Run the script:

`0 - init.py`

This script simply reads the `init_model.sql` file and executes it against the database.

# Run the mappings

This step should occur after running the downloaders and transformers, found elsewhere in the repo. These mappings transform all the data sources into a single model and stack them up on top of each other so they can be easily matched together and compared. They are loaded into the table `pws_contributors` in PostGIS.

Run this script to execute all of the mappings:

`1 - mappings.py`

# Run the matching

Step through this script to match the data together:

`2 - matching.py`

Each match rule attempts to connect one or more of the systems with known PWS ID's (ECHO, FRS, SDWIS, UCMR) to one or more of the systems with unknown PWS ID's (TIGER, MHP). Since we don't know the PWS ID's, we rely on a variety of matches, such as state+name matches or spatial matches.

Once the matches are discovered, they are saved to the database.

# Generate the match report
Step through this script to generate match reports:

`3 - match_reports.py`

These reports allow you to browse the matches to develop an intuition of which match rules were successful and which ones weren't. It can be pretty hard to tell sometimes!

# Run the Superjoin

The "superjoin" takes all of these candidate matches and attempts to pick the best ones, yielding a single file where each PWS has a "best" lat/long (from ECHO, UCMR, or MHP), matches to exactly 0 or 1 TIGER, and exactly 0 or 1 MHP. 