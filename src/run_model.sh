#! /bin/bash

# start a timer
SECONDS=0

# run transform scripts

echo -e "\n\n--------------------------------------\n\n"
echo -e "Preprocessing data for model"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/model/01_preprocess.R');"

echo -e "\n\n--------------------------------------\n\n"
echo -e "Running linear model for wsb estimation"
echo -e "\n\n--------------------------------------\n\n"
Rscript -e "source('src/model/02_linear.R');"

# end the timer
t=$SECONDS
echo -e "\n\n--------------------------------------\n\n"
printf 'Time elapsed: %d minutes' "$(( t/60 ))"
echo -e "\n\n--------------------------------------\n\n"
