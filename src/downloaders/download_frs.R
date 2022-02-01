# download FRS centroids --------------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: EPA's Facility Reigstry Service (FRS)
frs_url <- paste0("https://edg.epa.gov/data/public/OEI/FRS/",
                  "FRS_Interests_Download.zip")

# create dir to store file, download, and un-zip
dir_create(path(data_path, "frs"))
download.file(frs_url, path(data_path, "frs/frs.zip"))
unzip(path(data_path, "frs/frs.zip"), exdir = path(data_path, "frs"))
cat("Downloaded and unzipped FRS data.\n")
