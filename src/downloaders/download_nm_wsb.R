# Download NM water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: New Mexico ArcGIS geojson water system boundary
url <- paste0("https://catalog.newmexicowaterdata.org/dataset/",
              "5d069bbb-1bfe-4c83-bbf7-3582a42fce6e/resource/",
              "ccb9f5ce-aed4-4896-a2f1-aba39953e7bb/download/pws_nm.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/nm"))
download.file(url, path(data_path, "boundary/nm/nm.geojson"))
cat("Downloaded NM polygon boundary data.\n")
