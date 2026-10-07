"""
Generate Supplementary Fig. S1: sensitivity of forest travel time to the
canopy cover threshold used to define "forest" (25%, 50%, 75%), following
the same map style/colormap as Fig. 1 and Supplementary Fig. S2.

Inputs (native ~1 km resolution, motorised travel time, masked at 3 h):
  - 25%: Data/Latest/JRC_GFC2020_V2_mean_25_patch_motorized_sum_masked_3h.tif
  - 50%: Data/Latest/JRC_GFC2020_V2_mean_50_patch_motorized_sum_masked_3h.tif
         (the file actually used in the main analysis; see
         Codes/travel_time_forestarea.py)
  - 75%: Data/Latest/JRC_GFC2020_V2_mean_75_patch_area_1.0_motorized_sum_masked_3h.tif
         (no unfiltered 75% file exists; the 1.0 km^2 minimum-patch-area
         variant was chosen as the closest match to the unfiltered 25%/50%
         files -- user-confirmed choice, 2026-08-19)

Each raster is block-averaged 25x25 native pixels (~23 km, matching the
"current paper choice" resolution used for Fig. 1/1w/2A) using an
unweighted block mean, exactly as done for Fig. 1 panel A.
"""
import paths  # input and output locations, from config.yaml
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import numpy as np
import rasterio
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from rasterio.plot import show
from palettable.cartocolors.diverging import Geyser_5

sys.path.insert(0, os.path.dirname(__file__))
import my_utils as mu  # type: ignore

DATA_DIR = os.path.join(paths.INPUT_DIR, "Latest")
FIG_DIR = paths.FIG_DIR

FILES = {
    "25%": "JRC_GFC2020_V2_mean_25_patch_motorized_sum_masked_3h.tif",
    "50%": "JRC_GFC2020_V2_mean_50_patch_motorized_sum_masked_3h.tif",
    "75%": "JRC_GFC2020_V2_mean_75_patch_area_1.0_motorized_sum_masked_3h.tif",
}
LABELS = {"25%": "A", "50%": "B", "75%": "C"}
BLOCK = (25, 25)

cmap = Geyser_5.mpl_colormap.copy()
cmap.set_bad(color="white", alpha=0)
bounds = [0, 1, 2, 3, 4, 5, 10, 15, 30, 60, 90, 120, 180]
norm = mcolors.BoundaryNorm(bounds, ncolors=256)
sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])

fig, axes = plt.subplots(
    1, 3, figsize=(16, 5.2),
    subplot_kw={"projection": ccrs.PlateCarree()},
)

for ax, (pct, fname) in zip(axes, FILES.items()):
    path = os.path.join(DATA_DIR, fname)
    with rasterio.open(path) as src:
        data = src.read(1).astype(float)
        data[data == src.nodata] = np.nan
        block = mu.compute_block_mean(data, BLOCK)
        transform = mu.get_new_transform(src.transform, BLOCK)

    show(block, transform=transform, ax=ax, cmap=cmap, norm=norm)
    ax.add_feature(cfeature.OCEAN, facecolor="white")
    ax.add_feature(cfeature.LAND, facecolor="#e1dfdf")
    gl = ax.gridlines(draw_labels=False)
    gl.xlines = gl.ylines = False
    ax.text(0.01, 0.99, LABELS[pct], transform=ax.transAxes,
             fontsize=18, fontweight="bold", va="top")
    ax.set_title(f"Canopy cover threshold: {pct}", fontsize=12)

cbar_ax = fig.add_axes([0.30, 0.06, 0.4, 0.03])
cbar = plt.colorbar(sm, cax=cbar_ax, orientation="horizontal",
                     boundaries=bounds,
                     ticks=[0, 1, 2, 3, 4, 5, 10, 15, 30, 60, 90, 120, 180])
cbar.set_label("Average travel time to forest [min]", fontsize=11, labelpad=5)
cbar.ax.tick_params(labelsize=9)

fig.suptitle(
    "Sensitivity of forest travel time to the canopy cover threshold",
    fontsize=13, y=0.98,
)
fig.subplots_adjust(bottom=0.16, top=0.88, wspace=0.05)

os.makedirs(FIG_DIR, exist_ok=True)
fout = os.path.join(FIG_DIR, "FigureS1_CanopyThreshold.pdf")
fig.savefig(fout, dpi=300, bbox_inches="tight")
print("saved", fout)
