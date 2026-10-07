"""
Quantify the urban-rural gradient in forest travel time (coauthor
feedback, 2026-08-27: "leverage data on urbanisation rates ... show
where urbanisation might most strongly affect the travel time to
forests"), using GHS-SMOD R2023A (Degree of Urbanisation, level 1) as
the companion dataset to GHS-POP, both from the JRC GHSL data package.

GHS-SMOD level-1 classes (see .clr / GHSL Data Package 2023 docs):
  10   Water
  11   Very low density rural
  12   Low density rural
  13   Rural cluster
  21   Suburban or peri-urban
  22   Semi-dense urban cluster
  23   Dense urban cluster
  30   Urban centre
We group 11-13 as "rural" and 21-30 as "urban" (water excluded).

The SMOD raster's native grid is offset from the travel-time/population
grid by a sub-pixel amount, so it is resampled (nearest-neighbour, it
is categorical) onto the exact travel-time grid rather than simply
cropped.
"""
import paths  # input and output locations, from config.yaml
import os
import sys

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import geopandas as gpd
from rasterio.features import rasterize

sys.path.insert(0, os.path.dirname(__file__))
import my_utils as mu  # type: ignore

BASE = os.path.join(os.path.dirname(__file__), "..")
POP_PATH = paths.inp("population")
TT_PATH = paths.inp("tt_gfc_50")
SMOD_PATH = paths.inp("ghs_smod")
SHP_PATH = paths.inp("macroregions")
OUT_CSV = paths.der("urban_rural_traveltime_by_macroregion.csv")

RURAL_CODES = [11, 12, 13]
URBAN_CODES = [21, 22, 23, 30]

with rasterio.open(TT_PATH) as tt_src, rasterio.open(POP_PATH) as pop_src:
    tt = tt_src.read(1).astype(float)
    tt_nodata = 255
    tt[tt == tt_nodata] = np.nan
    target_transform = tt_src.transform
    target_shape = tt_src.shape
    target_crs = tt_src.crs

    pop = pop_src.read(1, window=rasterio.windows.from_bounds(*tt_src.bounds, transform=pop_src.transform))
    pop = pop[:target_shape[0], :target_shape[1]].astype(float)

pop[pop < 0] = 0
pop[(pop > 0) & (pop <= 1)] = 1

# Resample GHS-SMOD (categorical -> nearest neighbour) onto the exact
# travel-time grid.
with rasterio.open(SMOD_PATH) as smod_src:
    smod = np.zeros(target_shape, dtype=np.int16)
    reproject(
        source=rasterio.band(smod_src, 1),
        destination=smod,
        src_transform=smod_src.transform,
        src_crs=smod_src.crs,
        dst_transform=target_transform,
        dst_crs=target_crs,
        resampling=Resampling.nearest,
    )

is_rural = np.isin(smod, RURAL_CODES)
is_urban = np.isin(smod, URBAN_CODES)
valid = ~np.isnan(tt) & (pop > 0)

def pw_mean(mask):
    m = mask & valid
    if m.sum() == 0 or pop[m].sum() == 0:
        return np.nan, 0.0
    return float(np.average(tt[m], weights=pop[m])), float(pop[m].sum())

g_urban_mean, g_urban_pop = pw_mean(is_urban)
g_rural_mean, g_rural_pop = pw_mean(is_rural)
print(f"GLOBAL  urban: mean_tt={g_urban_mean:.2f} min  pop={g_urban_pop/1e9:.3f}B")
print(f"GLOBAL  rural: mean_tt={g_rural_mean:.2f} min  pop={g_rural_pop/1e9:.3f}B")
print(f"GLOBAL  gap (rural - urban): {g_rural_mean - g_urban_mean:.2f} min")
print()

gdf = gpd.read_file(SHP_PATH).to_crs(target_crs)

rows = []
print(f"{'Region':<20}{'Urban TT':>10}{'Rural TT':>10}{'Gap':>8}{'Urb.Pop(M)':>12}{'Rur.Pop(M)':>12}")
for _, r in gdf.iterrows():
    region = r["custom_reg"]
    region_mask = rasterize(
        [(r.geometry, 1)], out_shape=target_shape, transform=target_transform,
        fill=0, dtype=np.uint8,
    ).astype(bool)

    u_mean, u_pop = pw_mean(is_urban & region_mask)
    r_mean, r_pop = pw_mean(is_rural & region_mask)
    gap = r_mean - u_mean if (not np.isnan(u_mean) and not np.isnan(r_mean)) else np.nan

    rows.append({
        "region": region, "urban_mean_tt": u_mean, "rural_mean_tt": r_mean,
        "gap_rural_minus_urban": gap, "urban_pop": u_pop, "rural_pop": r_pop,
    })
    print(f"{region:<20}{u_mean:>10.2f}{r_mean:>10.2f}{gap:>8.2f}{u_pop/1e6:>12.1f}{r_pop/1e6:>12.1f}")

import csv
os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
with open(OUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
print("\nsaved", OUT_CSV)
