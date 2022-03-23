#! /bin/bash

# start a timer
SECONDS=0

# run download scripts

echo -e "\n\n--------------------------------------\n\n"
echo -e "Downloading water system boundary data for states"
echo -e "\n\n--------------------------------------\n\n"
find src/downloaders/states -type f -name "*.R" -exec Rscript {} \;

echo -e "\n\n--------------------------------------\n\n"
echo -e "Downloading ECHO admin data"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/downloaders/download_echo.R');"

echo -e "\n\n--------------------------------------\n\n"
echo -e "Downloading FRS centroids"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/downloaders/download_frs.R');"

echo -e "\n\n--------------------------------------\n\n"
echo -e "Downloading mobile home parks point data"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/downloaders/download_mhp.R');"

echo -e "\n\n--------------------------------------\n\n"
echo -e "Downloading SDWIS data"
echo -e "\n\n--------------------------------------\n\n"
python src/downloaders/download_sdwis.py

echo -e "\n\n--------------------------------------\n\n"
echo -e "Downloading TIGRIS places and Natural Earth coastline"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/downloaders/download_tigris_ne.R');"

echo -e "\n\n--------------------------------------\n\n"
echo -e "Downloading SDWIS data ( delete this !!!! )"
echo -e "\n\n--------------------------------------\n\n"
python src/downloaders/download_sdwis.py

echo -e "\n\n--------------------------------------\n\n"
echo -e "Downloading UCMR occurrence data"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/downloaders/download_ucmr.R');"

# end the timer
t=$SECONDS
echo -e "\n\n--------------------------------------\n\n"
printf 'Time elapsed: %d minutes' "$(( t/60 ))"
echo -e "\n\n--------------------------------------\n\n"
