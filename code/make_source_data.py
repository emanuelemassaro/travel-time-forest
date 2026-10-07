"""Write the source data behind each figure and table as CSV, in data/source_data/<Figure or Table>/.

Reads only the derived files in data/derived/ (no original input data). The values are those plotted or
tabulated by the notebooks and scripts listed in the README; the formulas below are the same as in those
notebooks (Figure3.ipynb, Figure4.ipynb, gdpAnalysis.ipynb, statistics.ipynb). Map panels are written as one row
per 25 km block (cell centre longitude/latitude, value), blocks without data omitted.

Usage: python code/make_source_data.py
"""
import json
import os

import numpy as np
import pandas as pd
import rasterio

import paths
from constants import REGION_TO_CONTINENT

OUT = os.path.join(paths.ROOT, "data", "source_data")
WORLD_POP = 7830089931  # global population used as denominator in Table 1 and Figs 3B and 6 (as in the notebooks)
THRESHOLDS = [1, 5, 10, 15, 30, 45, 90, 120, 180]


def out(folder, name, df):
    d = os.path.join(OUT, folder)
    os.makedirs(d, exist_ok=True)
    df.to_csv(os.path.join(d, name), index=False)


def raster_csv(path, value_name, clean):
    with rasterio.open(path) as src:
        a = src.read(1).astype(float)
        a = clean(a, src)
        t = src.transform
    rows, cols = np.where(~np.isnan(a))
    lon = t.c + (cols + 0.5) * t.a
    lat = t.f + (rows + 0.5) * t.e
    return pd.DataFrame({"lon": np.round(lon, 4), "lat": np.round(lat, 4), value_name: a[rows, cols]})


def main():
    der = paths.der

    # ---- Figure 1 (Figure1.ipynb) ----
    def nodata_nan(a, src):
        a[a == src.nodata] = np.nan
        return a
    out("Fig1", "Fig1A_travel_time_25km_blocks.csv", raster_csv(
        der("rasters/JRC_GFC2020_V2_mean_50_patch_motorized_sum_masked_3h_block25x25.tif"),
        "mean_travel_time_min", nodata_nan))
    df = pd.read_csv(der("macroregion_traveltime.csv")).sort_values("travel_time")
    df["continent"] = df["region"].map(REGION_TO_CONTINENT)
    out("Fig1", "Fig1B_mean_travel_time_by_macroregion.csv",
        df.rename(columns={"travel_time": "mean_travel_time_min_unweighted"}))

    # ---- Figure 2 (Figure1a.ipynb) ----
    def nodata_neg_nan(a, src):
        a[a == src.nodata] = np.nan
        a[a < 0] = np.nan
        return a
    out("Fig2", "Fig2A_population_weighted_travel_time_25km_blocks.csv", raster_csv(
        der("rasters/travel_time_weighted_block25x25.tiff"), "pop_weighted_travel_time_min", nodata_neg_nan))
    df = pd.read_csv(der("population_by_macroregion_traveltime_weighted.csv")).sort_values("ttw")
    df["continent"] = df["region"].map(REGION_TO_CONTINENT)
    out("Fig2", "Fig2B_pop_weighted_travel_time_by_macroregion.csv",
        df.rename(columns={"ttw": "pop_weighted_travel_time_min"}))

    # ---- Figure 3 (Figure2.ipynb; bars from Figure3.ipynb -> fig2b.csv) ----
    def m9999_nan(a, src):
        return np.where(a == -9999, np.nan, a)
    out("Fig3", "Fig3A_population_within_10min_25km_blocks.csv", raster_csv(
        der("rasters/pop_10_block25x25.tiff"), "population_within_10min", m9999_nan))
    bars = pd.read_csv(der("fig2b.csv")).sort_values(["continent", "threshold_min"])
    out("Fig3", "Fig3B_cumulative_population_share_by_continent.csv",
        bars.rename(columns={"rel_pop": "population_share_pct"}))
    g = pd.read_csv(der("population_by_macroregion_traveltime.csv"))
    g = g.groupby("threshold_min")["population"].sum().reset_index()
    g["population_share_pct"] = 100 * g["population"] / WORLD_POP
    out("Fig3", "Fig3B_cumulative_population_share_global.csv", g)

    # ---- Figure 5 (gdpAnalysis.ipynb) ----
    reg = pd.read_csv(der("macroregion_pop_gdp_tt_average.csv"))
    reg["continent"] = reg["region"].map(REGION_TO_CONTINENT)
    out("Fig5", "Fig5A_gdp_per_capita_vs_travel_time.csv",
        reg[["region", "continent", "gdp_pc", "time", "population"]].rename(
            columns={"gdp_pc": "gdp_per_capita_ppp2011", "time": "mean_travel_time_min_unweighted"}))
    thr = pd.read_csv(der("macroregion_pop_gdp_traveltime.csv"))
    b = thr[thr["threshold_min"] == 10].copy()
    b["continent"] = b["region"].map(REGION_TO_CONTINENT)
    out("Fig5", "Fig5B_gdp_per_capita_within_10min.csv",
        b.sort_values("gdp_pc")[["region", "continent", "gdp_pc", "population"]].rename(
            columns={"gdp_pc": "gdp_per_capita_ppp2011_within_10min", "population": "population_within_10min"}))

    # ---- Figure 6 (Figure4.ipynb) ----
    px = pd.read_csv(der("travel_socio_eco_class.csv"))
    rows = []
    for grp, gg in px.groupby("income_group"):
        tot = gg["population"].sum()
        for t in THRESHOLDS:
            within = gg[gg["travel_time"] <= t]["population"].sum()
            rows.append({"income_group": grp, "threshold_min": t, "population_share_pct": 100 * within / tot,
                         "group_population": tot})
    out("Fig6", "Fig6_cumulative_share_by_income_group.csv", pd.DataFrame(rows))
    out("Fig6", "Fig6_cumulative_share_global.csv", g)

    # ---- Figures S3 and S4 (figure_S3_S4_covariate_scatters.py) ----
    rows180 = thr[thr["threshold_min"] == 180].set_index("region")
    clim = pd.read_csv(der("macroregion_pop_gdp_tt_climate.csv")).set_index("region")
    s3 = pd.DataFrame({"annual_precip_mm": clim["annual_precip_mm"],
                       "mean_travel_time_min_unweighted": rows180["time"],
                       "gdp_per_capita_ppp2011": rows180["gdp_pc"]}).reset_index()
    out("FigS3", "FigS3_precipitation_vs_travel_time_and_gdp.csv", s3)
    veh = json.load(open(der("vehicles_per_1000_by_macroregion.json")))
    s4 = pd.DataFrame([{"region": r, "vehicles_per_1000": veh[r]["veh_per_1000"],
                        "mean_travel_time_min_unweighted": rows180.loc[r, "time"],
                        "gdp_per_capita_ppp2011": rows180.loc[r, "gdp_pc"]} for r in sorted(veh)])
    out("FigS4", "FigS4_vehicles_vs_travel_time_and_gdp.csv", s4)

    # ---- Tables ----
    t1 = g.copy()
    t1["population_billion"] = t1["population"] / 1e9
    out("Table1", "Table1_cumulative_population_by_threshold.csv", t1)
    out("TableS1", "TableS1_urban_rural_travel_time_by_macroregion.csv",
        pd.read_csv(der("urban_rural_traveltime_by_macroregion.csv")))
    out("TableS2", "TableS2_travel_time_by_koppen_group.csv", pd.read_csv(der("koppen_stratified_stats_1km.csv")))
    out("TableS3", "TableS3_vehicles_gdp_travel_time.csv",
        s4.sort_values("vehicles_per_1000")[["region", "vehicles_per_1000", "gdp_per_capita_ppp2011",
                                             "mean_travel_time_min_unweighted"]])
    out("TableS4", "TableS4_ssp2050_by_macroregion.csv", pd.read_csv(der("ssp2050_macroregion_stats.csv")))
    print("source data written to", OUT)


if __name__ == "__main__":
    main()
