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

Add the postgis extension:

`CREATE EXTENSION postgis;`

Exit out of psql:

`exit`

Exit out of the docker container:

`exit`