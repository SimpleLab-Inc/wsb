# Tier 3 model 

_Last updated 2022-03-28_  

This subdirectory depends on `superjoin.py` output in the `staging_path`, and contains two scripts which preprocess data for the Tier 3 model, and then generate predictions and write those to the staging path for `src/combine_tiers.R` which compiles the final TEMM spatial layer. 

In order, run `01_preprocess.R` followed by `02_linear.R`.  

For preprocessing and modeling documentation, see: `src/analysis/sandbox/model_explore/model_march.html`.  

The code herein was originally prototyped in the "model_explore" Little Sandbox, which contains additional models (random forest, xgboost) and superseded code (archived preprocess and linear model scripts).