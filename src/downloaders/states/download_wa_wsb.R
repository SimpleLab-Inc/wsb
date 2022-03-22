# Download WA water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Washington ArcGIS Geodatabase water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
              "b09475f47a5a46ca90fe6a168fb22e6d_0.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/wa"))
download.file(url, path(data_path, "boundary/wa/wa.geojson"))
cat("Downloaded WA polygon boundary data.\n")