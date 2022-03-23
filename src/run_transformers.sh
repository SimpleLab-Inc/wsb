#! /bin/bash

# start a timer
SECONDS=0

# run transform scripts

echo -e "\n\n--------------------------------------\n\n"
echo -e "Transforming water system boundary data for states"
echo -e "\n\n--------------------------------------\n\n"
find src/transformers/states -type f -name "*.R" -exec Rscript {} \;

echo -e "\n\n--------------------------------------\n\n"
echo -e "Transforming ECHO data"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/transformers/transform_echo.R');"

echo -e "\n\n--------------------------------------\n\n"
echo -e "Transforming FRS centroids"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/transformers/transform_frs.R');"

echo -e "\n\n--------------------------------------\n\n"
echo -e "Transforming mobile home parks point data"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/transformers/transform_mhp.R');"

echo -e "\n\n--------------------------------------\n\n"
echo -e "Transforming SDWIS data"
echo -e "\n\n--------------------------------------\n\n"
find src/transformers -type f -name "transform_sdwis_*.py" -exec python {} \;

echo -e "\n\n--------------------------------------\n\n"
echo -e "Transforming TIGRIS places and Natural Earth coastline"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/transformers/transform_tigris_ne.R');"

echo -e "\n\n--------------------------------------\n\n"
echo -e "Transforming UCMR occurrence data"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/transformers/transform_ucmr.R');"

# end the timer
t=$SECONDS
echo -e "\n\n--------------------------------------\n\n"
printf 'Time elapsed: %d minutes' "$(( t/60 ))"
echo -e "\n\n--------------------------------------\n\n"
