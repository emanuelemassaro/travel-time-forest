"""
Re-run the climate-stratified forest-access analysis (Table 2 in the
manuscript) using the TRUE 1-km Koppen-Geiger classification (Beck et
al. 2018, Scientific Data) instead of the coarse 0.5-degree Kottek et
al. (2006) classification nearest-neighbour-resampled onto the native
grid (the approach used in the original analysis; see
Data/Geotiff/climate/koppen_maingroup_native.tif).

Reviewer comment (coauthor, 2026-08-27): "You are using a KG
classification at 55 km resolution, while the rest of your analysis is
at 1 km ... it might not be very convincing to reviewers given that
high resolution versions exist."

Inputs:
  - Population: Data/Geotiff/population/GlobPOP_Count_30arc_2020_I32.tiff
  - Travel time: Data/Latest/JRC_GFC2020_V2_mean_50_patch_motorized_sum_masked_3h.tif
  - Climate: Data/Geotiff/climate/Beck_KG_V1/Beck_KG_V1_present_0p0083.tif
    (present-day, 1980-2016, 1-km / 30 arc-sec resolution)

All three rasters share the exact same 30-arc-second grid phase
(verified: identical pixel size and integer-pixel-aligned origins), so
no resampling/interpolation is needed -- only cropping to the common
overlap window.

Output: Data/Output/koppen_stratified_stats_1km.csv, in the same format
as the existing Data/Output/koppen_stratified_stats.csv (0.5-degree
version), for direct comparison.
"""
import paths  # input and output locations, from config.yaml
import os
import sys

import numpy as np
import rasterio
from rasterio.windows import from_bounds

sys.path.insert(0, os.path.dirname(__file__))
import my_utils as mu  # type: ignore

BASE = os.path.join(os.path.dirname(__file__), "..")
POP_PATH = paths.inp("population")
TT_PATH = paths.inp("tt_gfc_50")
KG_PATH = paths.inp("koppen_beck_1km")
OUT_CSV = paths.der("koppen_stratified_stats_1km.csv")
OUT_TIF = paths.der("rasters/koppen_maingroup_beck1km.tif")

# Beck et al. 2018 legend.txt: 1-3 = A, 4-7 = B, 8-16 = C, 17-28 = D, 29-30 = E
GROUP_RANGES = {
    "Tropical (A)": range(1, 4),
    "Arid (B)": range(4, 8),
    "Temperate (C)": range(8, 17),
    "Continental (D)": range(17, 29),
    "Polar (E)": range(29, 31),
}
THRESHOLDS = [1, 5, 10, 15, 30, 45, 90, 120, 180]


def population_weighted_gini(tt, pop):
    """Population-weighted Gini coefficient of the travel-time
    distribution, via the trapezoidal approximation of the Lorenz
    curve area (matches the method described in the manuscript
    Methods, 'Regional analysis and statistics')."""
    order = np.argsort(tt)
    tt_sorted = tt[order]
    pop_sorted = pop[order]
    cum_pop = np.cumsum(pop_sorted)
    cum_tt_pop = np.cumsum(tt_sorted * pop_sorted)
    total_pop = cum_pop[-1]
    total_tt_pop = cum_tt_pop[-1]
    if total_pop == 0 or total_tt_pop == 0:
        return np.nan
    L = cum_tt_pop / total_tt_pop
    F = cum_pop / total_pop
    # trapezoidal area under Lorenz curve, prepending the (0,0) point
    F = np.concatenate([[0.0], F])
    L = np.concatenate([[0.0], L])
    B = np.trapz(L, F)
    return 1 - 2 * B


with rasterio.open(POP_PATH) as pop_src, \
     rasterio.open(TT_PATH) as tt_src, \
     rasterio.open(KG_PATH) as kg_src:

    assert pop_src.crs == tt_src.crs == kg_src.crs, "CRS mismatch"

    # Overlap bounds across all three (tt has the smallest extent)
    b = (
        max(pop_src.bounds.left, tt_src.bounds.left, kg_src.bounds.left),
        max(pop_src.bounds.bottom, tt_src.bounds.bottom, kg_src.bounds.bottom),
        min(pop_src.bounds.right, tt_src.bounds.right, kg_src.bounds.right),
        min(pop_src.bounds.top, tt_src.bounds.top, kg_src.bounds.top),
    )
    print("overlap bounds:", b)

    pop = pop_src.read(1, window=from_bounds(*b, transform=pop_src.transform))
    tt = tt_src.read(1, window=from_bounds(*b, transform=tt_src.transform))
    kg = kg_src.read(1, window=from_bounds(*b, transform=kg_src.transform))
    kg_transform = kg_src.window_transform(from_bounds(*b, transform=kg_src.transform))
    kg_crs = kg_src.crs

    # Trim to common minimum shape (guards against off-by-one from window rounding)
    min_rows = min(pop.shape[0], tt.shape[0], kg.shape[0])
    min_cols = min(pop.shape[1], tt.shape[1], kg.shape[1])
    pop = pop[:min_rows, :min_cols].astype(float)
    tt = tt[:min_rows, :min_cols].astype(float)
    kg = kg[:min_rows, :min_cols]

pop[pop < 0] = 0
pop[(pop > 0) & (pop <= 1)] = 1
tt_nodata = 255
valid = (tt != tt_nodata) & (pop > 0)

rows = []
for group_name, codes in GROUP_RANGES.items():
    mask = valid & np.isin(kg, list(codes))
    n_pixels = int(mask.sum())
    if n_pixels == 0:
        continue
    g_tt = tt[mask]
    g_pop = pop[mask]
    total_population = float(g_pop.sum())
    pop_weighted_mean_tt = float(np.average(g_tt, weights=g_pop))
    gini = population_weighted_gini(g_tt, g_pop)

    row = {
        "climate_group": group_name,
        "n_pixels": n_pixels,
        "total_population": total_population,
        "pop_weighted_mean_tt": pop_weighted_mean_tt,
        "gini": gini,
    }
    for th in THRESHOLDS:
        pct = 100.0 * g_pop[g_tt <= th].sum() / total_population
        row[f"pct_within_{th}min"] = pct
    rows.append(row)
    print(f"{group_name}: n={n_pixels:,} pop={total_population/1e9:.3f}B "
          f"mean_tt={pop_weighted_mean_tt:.1f}min gini={gini:.3f}")

import csv
os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
fieldnames = ["climate_group", "n_pixels", "total_population",
              "pop_weighted_mean_tt", "gini"] + [f"pct_within_{t}min" for t in THRESHOLDS]
with open(OUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print("saved", OUT_CSV)

# Save the reclassified 1-km main-group raster for provenance/reuse
maingroup = np.zeros(kg.shape, dtype=np.uint8)
code_to_group_id = {"Tropical (A)": 1, "Arid (B)": 2, "Temperate (C)": 3,
                     "Continental (D)": 4, "Polar (E)": 5}
for group_name, codes in GROUP_RANGES.items():
    maingroup[np.isin(kg, list(codes))] = code_to_group_id[group_name]
mu.save_raster(OUT_TIF, maingroup.astype(float), kg_transform, kg_crs, nodata=0)
print("saved", OUT_TIF)
