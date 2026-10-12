# Setup: add the study-constructed metrics (once per project)

Do this after the project's own setup sheet, in the same project folder and with its `.venv` active.

## homelab-data-platform

1. Copy `setup/constructed/homelab-data-platform/_study_constructed_metrics.yml` from this repository to `dbt_project/models/_study_constructed_metrics.yml` in your `homelab-data-platform` folder. Don't edit it.
2. Check its SHA-256 is `a4ac89831f5f2694c0b086eaffd2d1a1dfd64f8337f5f1e39a75737741c5053d`.
3. From `dbt_project/`, run `dbt parse`. No rebuild is needed: the new metrics reuse existing measures.
4. ✅ **Check:** `mf list metrics` now also shows metrics whose names start with `cm_`.

## revenue-intelligence

1. Copy `setup/constructed/revenue-intelligence/_study_constructed_metrics.yml` from this repository to `dbt/models/_study_constructed_metrics.yml` in your `revenue-intelligence` folder. Don't edit it.
2. Check its SHA-256 is `bd6b2565a07f0facaa5e4fd27636478808a0ebd4561cfcae05ff0bf865d42f53`.
3. From `dbt/`, run `dbt parse`. No rebuild is needed: the new metrics reuse existing measures.
4. ✅ **Check:** `mf list metrics` now also shows metrics whose names start with `cm_`.

## supply-chain-analytics-dbt

1. Copy `setup/constructed/supply-chain-analytics-dbt/_study_constructed_metrics.yml` from this repository to `models/_study_constructed_metrics.yml` in your `supply-chain-analytics-dbt` folder. Don't edit it.
2. Check its SHA-256 is `6c4beafd12a0786bf0e0d1fc49e02d46f7efe51a042682c324212b22ccb54b3a`.
3. From the project root, run `dbt parse`. No rebuild is needed: the new metrics reuse existing measures.
4. ✅ **Check:** `mf list metrics` now also shows metrics whose names start with `cm_`.

Remove the file after you have emailed your worksheet, so later packets see the project as published.

