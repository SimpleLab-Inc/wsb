# Sandbox

The sandbox houses EDA, sanity checks, feature engineering experiments, and other ad hoc analysis that should remain separate from the pipeline in `/src`.  

## Contributor guide

1. **Input**: All analyses on standardized data begin with downloading data from the web. At this point in time, to obtain an MVP, we do no snapshot or fix incoming data, thus is is possible that the results of the analysis (and hence the viability of the code in this project) depends on when the download modules are run. Nonetheless, sandbox processes depend on standardized data in `/data/staging`.   
2. **Output**: All output should be either a report, figure, or table and live on Github in `/src/analysis/figures` or `/src/analysis/tables`.
3. **Contributions**: 
  * number reports and analyses within `/src/analysis`.  
  * keep the root dir clean by ensuring that each script produces something useful, otherwise, archive it.    
  * strive to build functions `src/functions` that span scripts.  
  * keep track of scripts in the table of contents (below).  


## Table of contents

* `run.R` is an evolving pipeline script that iterates over scripts in the sandbox that will gradually move to production. 
* `setup.R` builds the sandbox directory structure  
* `01_sanity_checks.R` investigates common errors identified in the planning and proposes appraoches to mitigate these errors  
* `02_eda.R` explores `staging` to report on a variety of topics including: ...  
* `03_model_explore.R` experiments with a variety of statistical and machine learning models to predict boundaries, and reports on uncertainty and error 


* `/archive` for posterity  
* `/data_output` for large, .gitignored data  
* `/etc` contains dependencies for various reports  
* `/figures` contain figures from various analyses  
* `/tables` contain tables that are small enough to pushed to github  
 