"""
Project population and GDP per capita to 2050 under SSP1 (Sustainability)
and SSP3 (Regional Rivalry), holding the transport network AND forest
cover fixed at their 2020 state (coauthor feedback, 2026-08-27: "without
calculating travel time" -- i.e., re-weight the existing 2020
travel-time map by future population/income, not recompute it).

Method: population and GDP growth ratios (2050/2020) per macroregion
are taken from the IIASA SSP Basic Drivers release 3.2 (population:
IIASA-WiC POP 2025 model; GDP|PPP: OECD ENV-Growth 2025 model), computed
in Codes/ssp_2050_growth_ratios.py (not re-run here; see
Data/SSP/ssp_macroregion_growth.json).
Each 2020 population pixel is scaled by its macroregion's ratio to
produce a 2050 SSP-consistent population count, preserving today's
spatial distribution within each macroregion (a standard simplification
when a downscaled future population grid is not used).
The 2020 travel-time raster is then re-weighted by this 2050 population
to obtain SSP-consistent 2050 statistics.
GDP per capita for 2050 is obtained directly from the ratio of total
projected GDP to projected population per macroregion (both from the
same SSP source), and used to re-run the double-disadvantage quadrant
classification against the *same* $10,000/30-min thresholds used for
2020, so that the classification's meaning (fixed thresholds) is
comparable across time.

CAVEAT (stated explicitly in the manuscript): forest cover and the
motorised friction surface are held fixed at 2020 levels; this analysis
answers "how would exposure to today's accessibility landscape change
under 2050 demographic/economic trajectories", not "what forest access
will look like in 2050".
"""
import paths  # input and output locations, from config.yaml
import json
import os
import sys

import numpy as np
import rasterio
import geopandas as gpd
from rasterio.features import rasterize

sys.path.insert(0, os.path.dirname(__file__))

BASE = os.path.join(os.path.dirname(__file__), "..")
POP_PATH = paths.inp("population")
TT_PATH = paths.inp("tt_gfc_50")
SHP_PATH = paths.inp("macroregions")
GROWTH_PATH = paths.der("ssp_macroregion_growth.json")
OUT_CSV = paths.der("ssp2050_macroregion_stats.csv")

THRESHOLDS = [1, 5, 10, 15, 30, 45, 90, 120, 180]
SCENARIOS = ["SSP1", "SSP3"]

growth = json.load(open(GROWTH_PATH))

with rasterio.open(TT_PATH) as tt_src, rasterio.open(POP_PATH) as pop_src:
    tt = tt_src.read(1).astype(float)
    tt_nodata = 255
    tt[tt == tt_nodata] = np.nan
    target_shape = tt_src.shape
    target_transform = tt_src.transform
    target_crs = tt_src.crs

    pop2020 = pop_src.read(1, window=rasterio.windows.from_bounds(*tt_src.bounds, transform=pop_src.transform))
    pop2020 = pop2020[:target_shape[0], :target_shape[1]].astype(float)

pop2020[pop2020 < 0] = 0
pop2020[(pop2020 > 0) & (pop2020 <= 1)] = 1
valid_tt = ~np.isnan(tt)

gdf = gpd.read_file(SHP_PATH).to_crs(target_crs)

rows = []
global_pop = {s: 0.0 for s in SCENARIOS}
global_pop["2020"] = 0.0
global_weighted_tt_num = {s: 0.0 for s in SCENARIOS}
global_weighted_tt_num["2020"] = 0.0
global_threshold_pop = {s: {t: 0.0 for t in THRESHOLDS} for s in SCENARIOS + ["2020"]}

for _, r in gdf.iterrows():
    region = r["custom_reg"]
    if region not in growth:
        print(f"WARNING: no SSP growth data for region '{region}', skipping")
        continue
    region_mask = rasterize(
        [(r.geometry, 1)], out_shape=target_shape, transform=target_transform,
        fill=0, dtype=np.uint8,
    ).astype(bool)
    m = region_mask & valid_tt & (pop2020 > 0)
    region_pop2020 = pop2020[m]
    region_tt = tt[m]
    total_pop2020 = region_pop2020.sum()

    row = {"region": region, "total_pop_2020_B": total_pop2020 / 1e9}
    global_pop["2020"] += total_pop2020
    global_weighted_tt_num["2020"] += (region_tt * region_pop2020).sum()
    for th in THRESHOLDS:
        global_threshold_pop["2020"][th] += region_pop2020[region_tt <= th].sum()

    mean_tt_2020 = float(np.average(region_tt, weights=region_pop2020))
    row["mean_tt_2020"] = mean_tt_2020

    g = growth[region]
    for scenario in SCENARIOS:
        pop_ratio = g["pop"][f"ratio_{scenario}"]
        gdp_ratio = g["gdp"][f"ratio_{scenario}"]
        region_pop_future = region_pop2020 * pop_ratio
        total_pop_future = total_pop2020 * pop_ratio

        mean_tt_future = float(np.average(region_tt, weights=region_pop_future))
        row[f"mean_tt_{scenario}_2050"] = mean_tt_future
        row[f"total_pop_{scenario}_2050_B"] = total_pop_future / 1e9

        # GDP in billion USD_2017/yr, population in million -> USD/capita
        gdp_pc_2020 = g["gdp"]["base_2020"] / g["pop"]["base_2020"] * 1000
        gdp_pc_future = gdp_pc_2020 * gdp_ratio / pop_ratio
        row[f"gdp_pc_{scenario}_2050_usd"] = gdp_pc_future
        row["gdp_pc_2020_usd"] = gdp_pc_2020

        global_pop[scenario] += total_pop_future
        global_weighted_tt_num[scenario] += (region_tt * region_pop_future).sum()
        for th in THRESHOLDS:
            global_threshold_pop[scenario][th] += region_pop_future[region_tt <= th].sum()

    rows.append(row)

# global summary row
grow = {"region": "GLOBAL", "total_pop_2020_B": global_pop["2020"] / 1e9,
        "mean_tt_2020": global_weighted_tt_num["2020"] / global_pop["2020"]}
for scenario in SCENARIOS:
    grow[f"mean_tt_{scenario}_2050"] = global_weighted_tt_num[scenario] / global_pop[scenario]
    grow[f"total_pop_{scenario}_2050_B"] = global_pop[scenario] / 1e9
rows.append(grow)

import csv
os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
fieldnames = sorted({k for row in rows for k in row.keys()}, key=lambda x: (x != "region", x))
with open(OUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"{'Region':<20}{'TT 2020':>10}{'TT SSP1-50':>12}{'TT SSP3-50':>12}"
      f"{'GDPpc 2020':>12}{'GDPpc SSP1':>12}{'GDPpc SSP3':>12}")
for row in rows:
    print(f"{row['region']:<20}{row.get('mean_tt_2020',float('nan')):>10.1f}"
          f"{row.get('mean_tt_SSP1_2050',float('nan')):>12.1f}"
          f"{row.get('mean_tt_SSP3_2050',float('nan')):>12.1f}"
          f"{row.get('gdp_pc_2020_usd',float('nan')):>12.0f}"
          f"{row.get('gdp_pc_SSP1_2050_usd',float('nan')):>12.0f}"
          f"{row.get('gdp_pc_SSP3_2050_usd',float('nan')):>12.0f}")

print()
print("Global cumulative population share by threshold:")
print(f"{'min':<6}{'2020':>10}{'SSP1-2050':>12}{'SSP3-2050':>12}")
for th in THRESHOLDS:
    p2020 = 100 * global_threshold_pop["2020"][th] / global_pop["2020"]
    p1 = 100 * global_threshold_pop["SSP1"][th] / global_pop["SSP1"]
    p3 = 100 * global_threshold_pop["SSP3"][th] / global_pop["SSP3"]
    print(f"{th:<6}{p2020:>10.1f}{p1:>12.1f}{p3:>12.1f}")

print("\nsaved", OUT_CSV)
