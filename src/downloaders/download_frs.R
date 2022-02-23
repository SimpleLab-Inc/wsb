# download FRS centroids --------------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: EPA's Facility Registry Service (FRS)
frs_url <- paste0("https://edg.epa.gov/data/public/OEI/FRS/",
                  "FRS_Interests_Download.zip")
frs_comb_url <- paste0("https://ofmext.epa.gov/FLA/www3/state_files/",
                      "national_combined.zip")

# create dir to store file, download, and un-zip
dir_create(path(data_path, "frs"))

# local path to download files
file_frs <- path(data_path, "frs/frs.zip")
file_frs_comb <- path(data_path, "frs/frs_comb.zip")

download.file(frs_url, file_frs)
download.file(frs_comb_url, file_frs_comb)

unzip(file_frs, exdir = path(data_path, "frs"))
unzip(file_frs_comb, exdir = path(data_path, "frs"))

cat("Downloaded and unzipped FRS data.\n")