# Start a PostGIS Docker container

`docker run -e POSTGRES_PASSWORD=postgres -d --name postgis/postgis -p 5433:5432 -v postgres_volume:/var/lib/postgresql/data postgres`

Notes about this command:
- The database password will be "postgres". This is safe when run locally, but never use this on a server exposed to the internet.
- PostGIS will be available on port 5433
- The data will be stored in a named docker volume called `postgres_volume`. This will preserve your data even if the container is stopped and removed.

## Configure the database

Connect to the PostGIS server and run:

`create database wsb;`

Connect to the database and run:

`CREATE EXTENSION postgis;`