# Tier 3 model 

_Last updated 2022-03-28_  

This subdirectory depends on the postgis database, in particular the records created by `5-select_modeled_centroids.py`. It contains two scripts, one which preprocesses data for the Tier 3 model, and another that generates predictions and write those to the staging path for `src/combine_tiers.py`, which compiles the final TEMM spatial layer. 

In order, run `01_preprocess.R` followed by `02_linear.R`.  

For preprocessing and modeling documentation, see: `src/analysis/sandbox/model_explore/model_march.html`.  

The code herein was originally prototyped in the "model_explore" Little Sandbox, which contains additional models (random forest, xgboost) and superseded code (archived preprocess and linear model scripts).
