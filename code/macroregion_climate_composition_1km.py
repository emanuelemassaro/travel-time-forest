"""
Recompute the population-weighted Koppen-Geiger main-group composition
of the four "double disadvantage" macroregions (Northern Africa,
Central Asia, Southern Asia, Western Africa), using the TRUE 1-km
Beck et al. (2018) classification instead of the 0.5-degree
Kottek et al. (2006) classification used in the original analysis.

Reproduces the numbers quoted in the Discussion:
  "Northern Africa (76% arid climate) and Central Asia (41% arid, 36%
  continental with limited precipitation) are predominantly
  climate-limited. By contrast, Western Africa (73% tropical) and
  Southern Asia (75% tropical or temperate) sit mostly within
  climatically forest-capable zones"

Uses the same aligned grid/arrays as climate_stratification_1km.py.
"""
import paths  # input and output locations, from config.yaml
import os
import sys

import numpy as np
import rasterio
import geopandas as gpd
from rasterio.windows import from_bounds
from rasterio.features import rasterize

sys.path.insert(0, os.path.dirname(__file__))

BASE = os.path.join(os.path.dirname(__file__), "..")
POP_PATH = paths.inp("population")
KG_PATH = paths.inp("koppen_beck_1km")
SHP_PATH = paths.inp("macroregions")

GROUP_RANGES = {
    "A": range(1, 4),   # Tropical
    "B": range(4, 8),   # Arid
    "C": range(8, 17),  # Temperate
    "D": range(17, 29), # Continental
    "E": range(29, 31), # Polar
}
REGIONS = ["Northern Africa", "Central Asia", "Southern Asia", "Western Africa"]

with rasterio.open(POP_PATH) as pop_src, rasterio.open(KG_PATH) as kg_src:
    b = (
        max(pop_src.bounds.left, kg_src.bounds.left),
        max(pop_src.bounds.bottom, kg_src.bounds.bottom),
        min(pop_src.bounds.right, kg_src.bounds.right),
        min(pop_src.bounds.top, kg_src.bounds.top),
    )
    pop = pop_src.read(1, window=from_bounds(*b, transform=pop_src.transform))
    kg = kg_src.read(1, window=from_bounds(*b, transform=kg_src.transform))
    transform = kg_src.window_transform(from_bounds(*b, transform=kg_src.transform))
    raster_crs = kg_src.crs

    min_rows = min(pop.shape[0], kg.shape[0])
    min_cols = min(pop.shape[1], kg.shape[1])
    pop = pop[:min_rows, :min_cols].astype(float)
    kg = kg[:min_rows, :min_cols]

pop[pop < 0] = 0
pop[(pop > 0) & (pop <= 1)] = 1

gdf = gpd.read_file(SHP_PATH).to_crs(raster_crs)

print(f"{'Region':<18}" + "".join(f"{g:>8}" for g in GROUP_RANGES) + f"{'Pop (B)':>10}")
for region in REGIONS:
    geom = gdf.loc[gdf["custom_reg"] == region, "geometry"]
    if geom.empty:
        print(f"Region '{region}' not found in shapefile")
        continue
    region_mask = rasterize(
        [(geom.iloc[0], 1)],
        out_shape=kg.shape,
        transform=transform,
        fill=0,
        dtype=np.uint8,
    ).astype(bool)

    region_pop = pop[region_mask]
    region_kg = kg[region_mask]
    total_pop = region_pop.sum()

    shares = {}
    for g, codes in GROUP_RANGES.items():
        m = np.isin(region_kg, list(codes))
        shares[g] = 100.0 * region_pop[m].sum() / total_pop if total_pop > 0 else np.nan

    print(f"{region:<18}" + "".join(f"{shares[g]:>7.1f}%" for g in GROUP_RANGES)
          + f"{total_pop/1e9:>10.3f}")
