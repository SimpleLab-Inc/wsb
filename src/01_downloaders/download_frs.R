# download FRS centroids --------------------------------------------------

library(here)

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: EPA's Facility Reigstry Service (FRS)
frs_url <- paste0("https://edg.epa.gov/data/public/OEI/FRS/",
                 "FRS_Interests_Download.zip")

# create dir to store file, download, and un-zip
fs::dir_create(here("data/frs"))
download.file(frs_url, here("data/frs/frs.zip"))
unzip(here("data/frs/frs.zip"), exdir = here("data/frs"))
cat("Downloaded and unzipped FRS data.\n")
