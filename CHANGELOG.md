# Water Service Boundaries - Change Log

# 2.0.0 (2022-07-01)
* No longer dropping any PWS's (but some results have tier "none", indicating no geometry)
* Added Utah labeled boundaries
* Eliminated Tier 2b by implement ranking and selection of best PWS per Tiger. Roughly 3000 became Tier 2a, remaining 7000 became Tier 3
* Renamed some columns:
  * geometry_lat -> centroid_lat
  * geometry_lon -> centroid_lon
  * geometry_quality -> centroid_quality
  * tiger_geoid -> matched_bound_geoid
  * tiger_name -> matched_bound_name
* Cleaned up column names in the shapefile
* Improved matching to MHPs, and prevented MHP's from matching to Tiger places
* Pulled in population data for Tiger places, to help deduplicate matches
* Misc bugfixes and performance improvements

| Tier 1  | Tier 2a | Tier 2b  | Tier 3  | None   | Total  |
|---------|---------|----------|---------|--------|--------|
| 15,784  | 12,436  | 0        | 17,722  | 3,482  | 49,424 |


# 1.0.0 (2022-05-02)
Initial release

| Tier 1  | Tier 2a | Tier 2b  | Tier 3  | None  | Total   |
|---------|---------|----------|---------|-------|---------|
| 14,607  | 9,488   | 10,104   | 10,720  | 0     | 44,919* |

*Note: 4505 systems were dropped due to missing geometry or not falling within 50 US states.
