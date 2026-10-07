# Global travel time to forest: code and derived data

Code and derived data for the manuscript *Global travel time to forest: accessibility patterns and socioeconomic
disparities* (Massaro, Ceccherini, Roebroek, Serkan, Cescatti; submitted to Nature Communications).
Manuscript version used for this package: `Paper/main_preview_August19.tex` (6 October 2026).

The package holds the scripts and notebooks that produce the figures, tables and numbers of that version, the
derived tables and rasters they write, the 17-macroregion boundary file, and the source data behind each figure and
table as CSV. The original input datasets are not included; section 3 lists them and where the code expects them.

The analysis code is the authors' latest version with one kind of edit: every hard-coded path was replaced with a
lookup in `config.yaml` (through `code/paths.py`). The logic is unchanged. Notebook outputs were cleared, and in
`Figure1a.ipynb` two exploratory cells after the saved figure were removed. Those cells drew an unsaved map from a
file that the paper does not use. Section 7 lists suspected bugs; they are reported here, not fixed.

## 1. Contents

```
README.md, LICENSE, requirements.txt, config.yaml, .gitignore
code/
  paths.py                         paths from config.yaml (added for this package)
  constants.py, my_utils.py        shared helpers (region -> continent, colours; raster functions)
  convert_netcdf_to_geotiff.py     GDP NetCDF (Kummu et al.) -> GeoTIFF, year 2015
  regions_travel_time.py           unweighted mean travel time per macroregion
  population_regions.py            population per macroregion
  population_per_travel_time.py    cumulative population within each threshold, per macroregion
  population_gdp_travel_time.py    pixel table: travel time, population, GDP per capita, income group
  climate_stratification_1km.py    statistics per Koppen-Geiger main group (1 km)
  macroregion_climate_composition_1km.py  climate composition of the double-disadvantage regions (printed)
  urban_rural_gradient.py          urban and rural travel time per macroregion (GHS-SMOD)
  ssp_2050_projection.py           2050 re-weighting under SSP1 and SSP3
  vehicle_ownership_covariate.py   vehicles per 1,000 people per macroregion; correlations (printed)
  figure_S1_canopy_threshold.py    Fig. S1
  figure_S3_S4_covariate_scatters.py  Figs S3 and S4
  make_source_data.py              writes data/source_data/ from data/derived/ (added for this package)
notebooks/
  Figure1.ipynb  Figure1a.ipynb  Figure2.ipynb  Figure3.ipynb  gdpAnalysis.ipynb  Figure4.ipynb  statistics.ipynb
data/
  macroregions/                    17 UN macroregions, shapefile (World Mollweide; field custom_reg)
  derived/                         tables and rasters written by the code (section 8)
  source_data/<Figure or Table>/   values behind each figure and table, CSV (section 8)
check/
  verify_manuscript_numbers.py     recomputes the manuscript numbers from data/derived/ (added for this package)
  verification_results.csv        result of the last run
```

The notebook and figure file names come from an earlier figure order. In the manuscript:

| Manuscript | Figure file | Produced by |
|---|---|---|
| Fig. 1 | Figure1AB.pdf | notebooks/Figure1.ipynb |
| Fig. 2 | Figure1ABw.pdf | notebooks/Figure1a.ipynb |
| Fig. 3 | Figure2AB.pdf | notebooks/Figure2.ipynb (bars from notebooks/Figure3.ipynb -> fig2b.csv) |
| Fig. 4 | Figure_Type_ForestsABC.pdf | **missing** (section 6) |
| Fig. 5 | Figure3AB.pdf | notebooks/gdpAnalysis.ipynb |
| Fig. 6 | Figure4.pdf | notebooks/Figure4.ipynb |
| Fig. S1 | FigureS1_CanopyThreshold.pdf | code/figure_S1_canopy_threshold.py |
| Fig. S2 | FigureS2_ok.pdf | **missing** (section 6) |
| Figs S3, S4 | FigureS3_ClimateCovariate.pdf, FigureS4_VehicleCovariate.pdf | code/figure_S3_S4_covariate_scatters.py |

## 2. Setup

Python 3.9.6 was used (macOS, Apple silicon). Install the packages with the versions used:

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` lists the versions installed in the environment of the last runs (August to October 2026).
The scripts written in 2025 may have been run with older versions; those versions were not recorded. `rioxarray`
(needed only by `convert_netcdf_to_geotiff.py`) was not installed in that environment, so its version is unknown.

Paths: edit `config.yaml`. The macroregion shapefile is read from `data/macroregions/`. `input_dir` (default `data/input`, or the environment variable `TTF_INPUT_DIR`) is the
folder holding the original datasets in the layout given in section 3. Scripts write to `data/derived/` and
`figures/`. Run scripts from the package root (`python code/<script>.py`) and notebooks from `notebooks/`.

## 3. Input data (not included)

Paths are relative to `input_dir`, except the macroregions (shipped in `data/macroregions/`). These are the files and
versions the code reads. Licences were checked on the providers' pages on 7 October 2026;
`<TO CONFIRM>` marks what could not be confirmed.

| Dataset | Provider, version | DOI or URL | Licence | Path expected by the code | Used by |
|---|---|---|---|---|---|
| Travel time to the nearest forest, motorised, masked at 180 min; forest = GFC2020 V2 canopy cover >= 50%, connected patches | Computed by co-author G. Serkan from GFC2020 V2 and the MAP friction surface 2019 (computation code not in this package, section 6) | not public: `<TO DEPOSIT>` | `<TO CONFIRM>` | `Latest/JRC_GFC2020_V2_mean_50_patch_motorized_sum_masked_3h.tif` | all main results |
| Same, canopy cover >= 25% | as above | `<TO DEPOSIT>` | `<TO CONFIRM>` | `Latest/JRC_GFC2020_V2_mean_25_patch_motorized_sum_masked_3h.tif` | Fig. S1 |
| Same, canopy cover >= 75%, minimum patch area 1 km2 | as above | `<TO DEPOSIT>` | `<TO CONFIRM>` | `Latest/JRC_GFC2020_V2_mean_75_patch_area_1.0_motorized_sum_masked_3h.tif` | Fig. S1 |
| Travel time to forest by GFT2020 type (classes 1, 10, 20) | as above, from GFT2020 V0 | `<TO DEPOSIT>` | `<TO CONFIRM>` | `Geotiff/travel_time/V0/JRC_GFT2020_V0_{1,10,20}_mean_50_patch_motorized_sum_masked_3h.tif` | Fig. 4 (script missing) |
| Global Forest Cover 2020 (GFC2020), version 2 | European Commission JRC | doi:10.3390/land12091724 (paper); https://forest.jrc.ec.europa.eu/ | CC BY 4.0 | (input of the travel-time computation only) | |
| Global Forest Type 2020 (GFT2020), version 0 (documented as V1 in doi:10.2760/9982436) | European Commission JRC | https://forest.jrc.ec.europa.eu/ | `<TO CONFIRM>` | (input of the travel-time computation only) | |
| Motorised friction surface 2019 | Malaria Atlas Project (Weiss et al. 2020, doi:10.1038/s41591-020-1059-1) | https://malariaatlas.org/ | CC BY 4.0 | (input of the travel-time computation only) | |
| GlobPOP, count, 30 arc-sec, 2020, Int32 | Liu et al. 2024 (doi:10.1038/s41597-024-02913-0), Zenodo v2.0 (2020 layer identical to v1.0) | doi:10.5281/zenodo.11179644 | CC BY 4.0 | `Geotiff/population/GlobPOP_Count_30arc_2020_I32.tiff` | all population results |
| Gridded GDP PPP, 30 arc-sec, v3 (NetCDF) | Kummu et al. 2018 (doi:10.1038/sdata.2018.4) | doi:10.5061/dryad.dk1j0 | CC0 (Dryad) | `Geotiff/gdp/GDP_PPP_30arcsec_v3.nc` | GDP results, Fig. 6 |
| Gridded GDP per capita PPP 1990-2015, 5 arc-min, v2 (NetCDF) | Kummu et al. 2018 | as above | CC0 (Dryad) | `Geotiff/gdp/GDP_per_capita_PPP_1990_2015_v2.nc` | (converted; not read by the current analysis, see section 7) |
| Koppen-Geiger classification, present 1980-2016, 0.0083 deg, V1 | Beck et al. 2018 (doi:10.1038/sdata.2018.214) | doi:10.6084/m9.figshare.6396959 | `<TO CONFIRM>` | `Geotiff/climate/Beck_KG_V1/Beck_KG_V1_present_0p0083.tif` | Table S2, climate composition |
| WorldClim 2.1, BIO12 annual precipitation, 5 arc-min | Fick and Hijmans 2017 (doi:10.1002/joc.5086) | https://www.worldclim.org/data/worldclim21.html | free for academic and non-commercial use; no redistribution | `Geotiff/climate/wc2.1_5m_bio_12.tif` | Fig. S3 |
| WorldClim 2.1, BIO1 annual mean temperature, 5 arc-min | as above | as above | as above | `Geotiff/climate/wc2.1_5m_bio_1.tif` | climate partial correlation (script missing) |
| GHS-SMOD R2023A, epoch 2020, WGS84, 30 arc-sec, V2.0 | European Commission JRC (Schiavina et al. 2023) | doi:10.2905/A0DF7A6F-49DE-46EA-9BDE-563437A6E2BA | CC BY 4.0 (`<TO CONFIRM>`) | `Geotiff/urbanisation/GHS_SMOD_E2020_GLOBE_R2023A_4326_30ss_V2_0.tif` | Table S1 |
| 17 UN macroregions (custom shapefile, World Mollweide; field `custom_reg`) | authors, from UN M49 (Caribbean, Central and South America merged; Oceania merged) | included in this package | as the derived data (section 10) | `data/macroregions/world-custom_regions_r.shp` (package root) | all regional results |
| SSP Basic Drivers, release 3.2 (population IIASA-WiC POP 2025, GDP OECD ENV-Growth 2025) | IIASA | https://ssp.apps.ece.iiasa.ac.at/ (`<DOI TO CONFIRM>`) | `<TO CONFIRM>` | read only by the missing script `ssp_2050_growth_ratios.py` (local file `SSP/ssp_basic_drivers_release_3.2_full.xlsx`) | Table S4 |
| Registered vehicles (indicator RS_194) | WHO Global Health Observatory | https://ghoapi.azureedge.net/api/RS_194 (fetched at run time) | CC BY-NC-SA 3.0 IGO | fetched by `vehicle_ownership_covariate.py`; no snapshot kept | Table S3, Fig. S4 |
| Population (SP.POP.TOTL), 2007-2017 | World Bank | https://api.worldbank.org/v2/ (fetched at run time) | CC BY 4.0 | as above | Table S3, Fig. S4 |
| UN M49 area codes | `un-m49` npm package (via unpkg) | `<VERSION TO CONFIRM>` | `<TO CONFIRM>` | used only to build `data/derived/unm49_by_code.json` (script missing) | Table S3, Fig. S4 |

All rasters share the 30 arc-second grid (the travel-time rasters cover 60 S to 85 N; GlobPOP and GDP cover
90 S to 90 N).

## 4. Order of the steps

Heavy steps read global 1 km rasters (43,200 x 21,600 or 43,200 x 17,400 pixels). Light steps read only
`data/derived/`. Runtimes were measured on a MacBook with 16 GB RAM and 10 cores where stated. The other heavy
steps were not re-run for this package; their memory needs are estimated from the array sizes.

| # | Step | Reads | Writes | Runtime, memory |
|---|---|---|---|---|
| 1 | `code/convert_netcdf_to_geotiff.py` | GDP NetCDF | `derived/rasters/GDP_PPP_2015.tif`, `GDP_per_capita_PPP_2015.tif` | not measured; about 4 GB array |
| 1b | compress `GDP_PPP_2015.tif` -> `GDP_PPP_2015_compressed.tif` | | | **no script** (section 6) |
| 2 | `code/regions_travel_time.py` | travel time, macroregions | `macroregion_traveltime.csv` | not measured; per-region masks, a few GB |
| 3 | `code/population_regions.py` | population, macroregions | `population_by_macroregion.csv` | not measured |
| 4 | `code/population_per_travel_time.py` | population, travel time, macroregions | `population_by_macroregion_traveltime.csv` | not measured |
| 5 | `code/population_gdp_travel_time.py` | population, travel time, GDP (compressed) | `travel_socio_eco_class.csv` (367 MB) | not measured. The calls that wrote `macroregion_pop_gdp_traveltime.csv` and `macroregion_pop_gdp_tt_average.csv` are commented out in the latest version (lines 15, 18, 19) |
| 6 | `code/climate_stratification_1km.py` | population, travel time, Koppen-Geiger | `koppen_stratified_stats_1km.csv`, `rasters/koppen_maingroup_beck1km.tif` (5.4 GB) | not measured; about 12 GB RAM |
| 7 | `code/macroregion_climate_composition_1km.py` | population, Koppen-Geiger, macroregions | printed only | **25 s, 6.0 GB peak** |
| 8 | `code/urban_rural_gradient.py` | population, travel time, GHS-SMOD, macroregions | `urban_rural_traveltime_by_macroregion.csv` (global row printed only) | not measured; about 14 GB RAM |
| 9 | `ssp_2050_growth_ratios.py` | SSP spreadsheet | `ssp_macroregion_growth.json` | **no script** (section 6) |
| 10 | `code/ssp_2050_projection.py` | population, travel time, macroregions, growth ratios | `ssp2050_macroregion_stats.csv` (threshold shares printed only) | not measured; about 14 GB RAM |
| 11 | crosswalk (UN M49) | `un-m49` package | `unm49_by_code.json`, `country_to_macro.json` | **no script** (section 6) |
| 12 | `code/vehicle_ownership_covariate.py` | WHO and World Bank APIs (online), crosswalk, `macroregion_pop_gdp_traveltime.csv` | `vehicles_per_1000_by_macroregion.json`; correlations printed | seconds; needs internet |
| 13 | `code/figure_S1_canopy_threshold.py` | the three canopy-threshold travel-time rasters | `figures/FigureS1_CanopyThreshold.pdf` | not measured; about 6 GB per raster |
| 14 | `notebooks/statistics.ipynb` | population, travel time, derived tables | printed | **45 s** |
| 15 | `notebooks/Figure3.ipynb` | derived tables | `fig2b.csv` | light, 3 s |
| 16 | `notebooks/Figure1.ipynb`, `Figure1a.ipynb`, `Figure2.ipynb`, `gdpAnalysis.ipynb`, `Figure4.ipynb` | derived tables and 25 km rasters | Figs 1, 2, 3, 5, 6 | light, 2-7 s each |
| 17 | `code/figure_S3_S4_covariate_scatters.py` | WorldClim BIO12, macroregions, derived tables | Figs S3, S4 | light, 3 s |
| 18 | `code/make_source_data.py` | `data/derived/` | `data/source_data/` | light, 7 s |
| 19 | `check/verify_manuscript_numbers.py` | `data/derived/` | `check/verification_results.csv` | light, 10 s |

The 25 km block rasters used by Figs 1-3 (`data/derived/rasters/*_block25x25.*`) have no producing script
(section 6). They are included as derived data.

## 5. Figures, tables and numbers -> code

| Manuscript item | Value(s) | Code | Derived file |
|---|---|---|---|
| Table 1; abstract (51.7%, 4.05 bn, 74.2%); Results (96.0% within 3 h) | cumulative population | `population_per_travel_time.py`; printed by `statistics.ipynb` | `population_by_macroregion_traveltime.csv` |
| Total population 7.83 bn | constant 7,830,089,931 in the notebooks | none (hard-coded). Equals the sum of the GlobPOP 2020 raster (checked) | |
| Fig. 1; regional means (2.2 ... 85.2 min; "almost 40-fold") | unweighted pixel means | `regions_travel_time.py`; `Figure1.ipynb` | `macroregion_traveltime.csv`, `rasters/JRC_..._block25x25.tif` |
| Fig. 2; 21.7 min population-weighted global mean | | `Figure1a.ipynb`; 21.7 from `statistics.ipynb` | `population_by_macroregion_traveltime_weighted.csv` (producer missing; possible bug, section 7), `rasters/travel_time_weighted_block25x25.tiff` |
| Fig. 3; Europe over 85% within 10 min | | `Figure2.ipynb`, `Figure3.ipynb` | `fig2b.csv`, `rasters/pop_10_block25x25.tiff` |
| Fig. 4 (forest types) | | **missing** | |
| Fig. 5; Spearman -0.39 (p=0.125), weighted Pearson -0.45; quadrant values; double disadvantage 2.67 bn, 34%; 1.94 bn | | `gdpAnalysis.ipynb`, `statistics.ipynb` | `macroregion_pop_gdp_tt_average.csv`, `macroregion_pop_gdp_traveltime.csv` |
| Fig. 6; 70.1% vs 56.8%, gap 13.4 pp at 10 min, 13.6 pp at 5 min | | `population_gdp_travel_time.py`, `Figure4.ipynb` | `travel_socio_eco_class.csv` (possible bug, section 7) |
| Table S1; urban 21.0 vs rural 23.1 min | | `urban_rural_gradient.py` (global values printed only) | `urban_rural_traveltime_by_macroregion.csv` |
| Table S2; 2.6 to 3.7 times | | `climate_stratification_1km.py` | `koppen_stratified_stats_1km.csv` |
| Climate composition 78% / 77% / 72% / 67%; 2.35 bn (88%) | | `macroregion_climate_composition_1km.py` (printed) | |
| 0.5 deg vs 1 km comparison ("up to ~40%") | | **missing** | `koppen_stratified_stats_0p5deg.csv`, `macroregion_climate_composition_0p5deg.csv` |
| Precipitation vs travel time r=-0.77, vs GDP r=-0.04 (Fig. S3) | | `figure_S3_S4_covariate_scatters.py` | `macroregion_pop_gdp_traveltime.csv` |
| Partial r=-0.51 (p=0.035) controlling for temperature and precipitation | | **missing** | `macroregion_pop_gdp_tt_climate.csv` (producer missing) |
| Vehicles: r=-0.50 (p=0.042), r=0.94, partial r=0.26 (p=0.33); Table S3; Fig. S4 | | `vehicle_ownership_covariate.py`, `figure_S3_S4_covariate_scatters.py` | `vehicles_per_1000_by_macroregion.json` |
| Table S4; 21.8 / 22.3 / 22.7 min | | `ssp_2050_projection.py` | `ssp2050_macroregion_stats.csv` |
| Table S4 shares within 10 and 30 min (53.9 ... 76.3%) | | `ssp_2050_projection.py` (printed only) | |
| Table S4 double disadvantage 2.14 / 2.58 / 2.87 bn; 2050 classification with median thresholds | | **classification missing**; the values equal the sum of three regions in `ssp2050_macroregion_stats.csv` | |
| Fig. S1 | | `figure_S1_canopy_threshold.py` | |
| Fig. S2 and its table (21.4 to 30.9 min) | | **missing** | |

## 6. Missing pieces

Items of the manuscript with no script in the repository. They are listed, not reconstructed.

1. **Fig. 4 (travel time by forest type)**: no script or notebook produces `Figure_Type_ForestsABC.pdf`.
2. **Fig. S2 (resolution sensitivity) and its table** (native 21.4 to 100 km 30.9 min): no script.
3. **25 km block rasters** for Figs 1A, 2A and 3A (`*_block25x25.*`): no script. `resize_data.py` in the
   repository writes the earlier 50 km versions.
4. **`ssp_2050_growth_ratios.py`** (SSP spreadsheet -> `ssp_macroregion_growth.json`): not in the repository.
5. **2050 double-disadvantage classification** with median 2050 thresholds: no script. The docstring of
   `ssp_2050_projection.py` still describes fixed $10,000 / 30 min thresholds, which differs from Methods.
6. **Climate partial correlation** (r=-0.51, p=0.035) and the zonal means of BIO1 and BIO12 in
   `macroregion_pop_gdp_tt_climate.csv`: no script.
7. **0.5 degree Koppen-Geiger comparison** (Methods, "up to ~40%"): no script for `koppen_stratified_stats_0p5deg.csv`
   and `macroregion_climate_composition_0p5deg.csv`.
8. **UN M49 crosswalk** (`unm49_by_code.json`, `country_to_macro.json`, `ssp_country_to_macro.json`): built
   interactively, no script. The files are included.
9. **Producer of `macroregion_pop_gdp_traveltime.csv` and `macroregion_pop_gdp_tt_average.csv`**: the calls are
   commented out in `population_gdp_travel_time.py`. Re-enabling them is a code change, so it was not done here.
10. **Producer of `population_by_macroregion_traveltime_weighted.csv`** (Fig. 2B): the latest
    `travel_time_populatedarea.py` writes a `_10` variant (GFT2020 class 10) instead.
11. **`GDP_PPP_2015_compressed.tif`**: a compressed copy of `GDP_PPP_2015.tif`, no script.
12. **Travel-time computation** (least-cost path on the MAP friction surface) for all travel-time rasters: done by
    a co-author, code not in the repository.
13. **Snapshot of the WHO and World Bank API responses** used for Table S3. The script fetches them at run time,
    so a new run can give different values.
14. **`vehicles_per_1000_by_macroregion.csv`**: the script writes only the JSON (same values).

## 7. Suspected bugs and inconsistencies (code left unchanged)

1. **Fig. 6 and the income-group results: travel time paired with population and GDP 5 degrees further north.**
   `my_utils.get_pixel_level_data_windowed` (called by `population_gdp_travel_time.py`) reads the travel-time,
   population and GDP rasters with the same pixel windows. The travel-time raster starts at 85 N, the other two at
   90 N, so every window of travel time is paired with population and GDP 600 rows (5 degrees, about 555 km)
   further north. Checked: the first window covers 80.7-85.0 N in the travel-time raster and 85.7-90.0 N in the
   population raster. The numbers 70.1%, 56.8%, 13.4 and 13.6 pp, and Fig. 6, come from this table.
2. **Fig. 2B: nodata counted as 255 minutes (likely).** The function that writes the population-weighted regional
   means (`regions_travel_time` in `travel_time_populatedarea.py`, not included) does not mask the value 255.
   `population_by_macroregion_traveltime_weighted.csv` gives Central Asia 95.8 min, Northern Africa 77.9, Western
   Asia 85.5. The correctly masked population-weighted means in `ssp2050_macroregion_stats.csv` are 57.7, 38.6 and
   37.3. The producer of the file is missing (section 6), so this is likely, not certain.
3. **Methods vs code for the income groups.** Methods says the 5 arc-min GDP per capita layer was bilinearly
   resampled to 1 km and classified. The code divides total GDP (30 arc-sec) by population per pixel and does not
   read the GDP-per-capita layer.
4. **Two GDP per capita values for the same region.** The Results text and Fig. 5 use whole-region GDP per capita
   (`macroregion_pop_gdp_tt_average.csv`). Table S3 and the vehicle and precipitation analyses use the GDP of pixels
   within 180 min (`macroregion_pop_gdp_traveltime.csv`, threshold 180). Central Asia: $9,758 in the text, $8,449 in
   Table S3. The text compares the vehicle partial correlation with "the unconditional r=-0.39 (p=0.125)", which
   comes from the other GDP series (p=0.122 with the Table S3 series).
5. **Different 2020 baselines in Table S4.** `ssp_2050_projection.py` keeps only pixels inside the macroregions with
   travel time up to 180 min (7.52 bn people) and uses population-weighted regional means. That gives 21.8 min,
   53.9% and 2.14 bn (three regions) for 2020, against 21.7 min, 51.7% and 2.67 bn (four regions) in the main
   results.
6. **Stale docstrings.** `macroregion_climate_composition_1km.py` quotes earlier numbers (76%, 41%); the script
   output matches the manuscript (78%, 77%). `ssp_2050_projection.py` describes fixed thresholds (item 5 of
   section 6).
7. **Three paths for one raster.** The 2025 scripts read the main travel-time raster from
   `Geotiff/travel_time/` (the file is no longer there), `statistics.ipynb` from `Geotiff/travel_time/V2/`, and the
   2026 scripts from `Latest/`. The `V2/` and `Latest/` files are identical (same MD5). This package reads `Latest/`.

## 8. Derived data, source data and sizes

`data/derived/` (written by the code; `rasters/` holds the display rasters):

| File | Size | Notes |
|---|---|---|
| travel_socio_eco_class.csv | 366.8 MB | **too large for GitHub: Zenodo**. See issue 1 of section 7 |
| rasters/JRC_GFC2020_V2_mean_50_patch_motorized_sum_masked_3h_block25x25.tif | 9.6 MB | Fig. 1A |
| rasters/GlobPOP_Count_30arc_2020_I32_block25x25.tiff | 9.6 MB | read by Figs 1, 2 notebooks |
| rasters/pop_10_block25x25.tiff | 4.8 MB | Fig. 3A |
| rasters/travel_time_weighted_block25x25.tiff | 4.8 MB | Fig. 2A |
| unm49_by_code.json | 25.5 kB | crosswalk |
| macroregion_pop_gdp_traveltime.csv | 13.8 kB | per region and threshold |
| ssp_macroregion_growth.json | 6.6 kB | SSP growth ratios |
| ssp_country_to_macro.json | 6.0 kB | crosswalk |
| country_to_macro.json | 5.9 kB | crosswalk |
| population_by_macroregion_traveltime.csv | 4.2 kB | Table 1 |
| ssp_macroregion_pop_gdp.json | 4.1 kB | SSP totals per region |
| ssp2050_macroregion_stats.csv | 3.3 kB | Table S4 |
| fig2b.csv | 2.2 kB | Fig. 3B |
| macroregion_pop_gdp_tt_climate.csv | 2.2 kB | climate zonal means |
| macroregion_climate_composition_0p5deg.csv | 1.9 kB | 0.5 deg comparison |
| urban_rural_traveltime_by_macroregion.csv | 1.7 kB | Table S1 |
| vehicles_per_1000_by_macroregion.json / .csv | 1.7 / 0.8 kB | Table S3 |
| macroregion_pop_gdp_tt_average.csv | 1.5 kB | Fig. 5A |
| koppen_stratified_stats_1km.csv | 1.3 kB | Table S2 |
| koppen_stratified_stats_0p5deg.csv | 0.9 kB | 0.5 deg comparison |
| population_by_macroregion_traveltime_weighted.csv | 0.8 kB | Fig. 2B (issue 2) |
| macroregion_traveltime.csv | 0.6 kB | Fig. 1B |
| population_by_macroregion.csv | 0.4 kB | totals |

`data/macroregions/` (shapefile, 4 files): 2.8 MB.

`data/source_data/` (written by `code/make_source_data.py`): Fig1 (7.2 MB), Fig2 (6.9 MB), Fig3 (6.2 MB), Fig5,
Fig6, FigS3, FigS4, Table1, TableS1-S4 (each under 4 kB). Map panels are one row per 25 km block (lon, lat,
value). Not available: Fig. 4 and Fig. S2 (no script); Fig. S1 (the script computes the maps in memory and does
not save them).

For Zenodo (not in the GitHub repository): `data/derived/travel_socio_eco_class.csv` (366.8 MB). Recommended as
well: the travel-time rasters of section 3 (6 files of about 45-105 MB: the three canopy thresholds and the three forest types of Fig. 4); they are the
paper's main product and are not public elsewhere. Every other file is under 10 MB; the whole package is 400 MB,
of which 367 MB is that one table.

## 9. Check of the light steps

From a copy of this folder, all seven notebooks, `figure_S3_S4_covariate_scatters.py`,
`macroregion_climate_composition_1km.py` and `check/verify_manuscript_numbers.py` were run (7 October 2026).

- Figs 1, 2, 3, S3 and S4 are pixel-identical to the manuscript figures (rendered at 60 dpi). Figs 5 and 6
  have the same content, with a 1-2 px difference in label layout.
- `fig2b.csv` regenerated byte-identical.
- `statistics.ipynb`: 21.7 min, 7.59 bn people, 67,313,240 pixels, Gini 0.703, Table 1, Spearman -0.387
  (p=0.125), weighted Pearson -0.454.
- Climate composition: Northern Africa 78.2% arid, Central Asia 77.3% arid, Western Africa 72.1% tropical,
  Southern Asia 36.6% + 30.6% = 67.2% tropical or temperate.
- The precipitation values in `macroregion_pop_gdp_tt_climate.csv` equal those computed by the Fig. S3 script.
- The GlobPOP 2020 raster sums to 7,830,089,931, the constant used in the notebooks.
- `verify_manuscript_numbers.py`: 166 numbers match, 7 differ, 3 inconsistencies between text and table,
  8 not verifiable from the derived files. Details in `check/verification_results.csv`.

## 10. Licence

Code: MIT (see LICENSE; copyright Emanuele Massaro and co-authors). Derived data and the macroregion shapefile:
`<LICENCE TO CONFIRM, e.g. CC BY 4.0>`, subject to the licences of the input datasets in section 3 (WorldClim does
not allow redistribution of its rasters; only regional means derived from it are included).
