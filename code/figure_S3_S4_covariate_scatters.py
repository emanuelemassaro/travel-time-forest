"""
Generate Supplementary Fig. S3 (climate covariate: precipitation) and
Fig. S4 (vehicle ownership covariate) scatter plots, visualising the
Spearman correlations reported in Results ("Climate as a determinant
of forest access" and the vehicle-ownership paragraph).

Fig. S3: precipitation vs travel time (r=-0.77) and vs GDP per capita
(r=-0.04), reproducing the unweighted macroregion zonal means used
throughout the manuscript (validated against the existing reported
r-values before plotting).
Fig. S4: vehicle ownership vs travel time (r=-0.50) and vs GDP per
capita (r=0.94), using Data/Output/vehicles_per_1000_by_macroregion.csv.
"""
import paths  # input and output locations, from config.yaml
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.features import rasterize
from scipy import stats

BASE = os.path.join(os.path.dirname(__file__), "..")
FIG_DIR = paths.FIG_DIR

rows = list(csv.DictReader(open(paths.der("macroregion_pop_gdp_traveltime.csv"))))
rows180 = {r["region"]: r for r in rows if r["threshold_min"] == "180"}
regions = sorted(rows180)
tt = {r: float(rows180[r]["time"]) for r in regions}
gdp = {r: float(rows180[r]["gdp_pc"]) for r in regions}


def scatter_panel(ax, x, y, xlabel, ylabel, log_x=False, log_y=False):
    labels = list(x.keys())
    xv = np.array([x[k] for k in labels])
    yv = np.array([y[k] for k in labels])
    ax.scatter(xv, yv, s=45, color="#2c7fb8", edgecolor="white", linewidth=0.6, zorder=3)
    for k in labels:
        ax.annotate(k, (x[k], y[k]), fontsize=6, alpha=0.75,
                     xytext=(3, 3), textcoords="offset points")
    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")
    r, p = stats.spearmanr(xv, yv)
    ax.text(0.03, 0.95, f"Spearman r = {r:.2f}\np = {p:.3f}",
             transform=ax.transAxes, va="top", fontsize=9,
             bbox=dict(boxstyle="round", facecolor="white", alpha=0.8, edgecolor="#999999"))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)


# ---------- Fig S3: climate (precipitation) covariate ----------
gdf = gpd.read_file(paths.inp("macroregions")).to_crs("EPSG:4326")
with rasterio.open(paths.inp("worldclim_bio12")) as p_src:
    precip_arr = p_src.read(1).astype(float)
    precip_arr[precip_arr == p_src.nodata] = np.nan
    transform, shape = p_src.transform, p_src.shape

precip = {}
for _, r in gdf.iterrows():
    region = r["custom_reg"]
    mask = rasterize([(r.geometry, 1)], out_shape=shape, transform=transform,
                      fill=0, dtype="uint8").astype(bool)
    precip[region] = float(np.nanmean(precip_arr[mask]))

fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
scatter_panel(axes[0], precip, tt, "Mean annual precipitation (mm/yr)",
              "Mean travel time to forest (min)")
scatter_panel(axes[1], precip, gdp, "Mean annual precipitation (mm/yr)",
              "GDP per capita (PPP $)", log_y=True)
fig.suptitle("Climate (precipitation) as a covariate of the GDP–access relationship", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fout = os.path.join(FIG_DIR, "FigureS3_ClimateCovariate.pdf")
fig.savefig(fout, dpi=300, bbox_inches="tight")
print("saved", fout)

# ---------- Fig S4: vehicle ownership covariate ----------
veh = json.load(open(paths.der("vehicles_per_1000_by_macroregion.json")))
veh_per_1000 = {r: veh[r]["veh_per_1000"] for r in regions if r in veh}

fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
scatter_panel(axes[0], veh_per_1000, {r: tt[r] for r in veh_per_1000},
              "Registered vehicles per 1,000 inhabitants", "Mean travel time to forest (min)")
scatter_panel(axes[1], veh_per_1000, {r: gdp[r] for r in veh_per_1000},
              "Registered vehicles per 1,000 inhabitants", "GDP per capita (PPP $)")
fig.suptitle("Vehicle ownership as a covariate of the GDP–access relationship", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fout = os.path.join(FIG_DIR, "FigureS4_VehicleCovariate.pdf")
fig.savefig(fout, dpi=300, bbox_inches="tight")
print("saved", fout)
