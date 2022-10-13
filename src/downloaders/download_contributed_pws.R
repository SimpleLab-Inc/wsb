# Download contributed public water system boundaries ---------------------
library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout for download file
options(timeout = 10000)

# Data Source: Current Github managed by CGS/IOW, where final, accepted
# individual contributor public water systems are added to SL's base map layer

contributed_pws_url <- paste0("https://github.com/cgs-earth/ref_pws/raw/main/02_output/",
                              "contributed_pws.gpkg")

# create dir to store file, download, and un-zip
dir_create(path(data_path, "contributed_pws"))

# local path to download files
file_contributed_pws <- path(data_path, "contributed_pws/contributed_pws.gpkg")

download.file(contributed_pws_url, file_contributed_pws, mode="wb")

cat("Downloaded contributed PWS data.\n")
