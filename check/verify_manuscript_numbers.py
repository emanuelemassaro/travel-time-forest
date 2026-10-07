"""Compare the numbers quoted in the manuscript with values recomputed from the derived data in data/derived/.

Each check formats the recomputed value at the precision used in the manuscript and compares the text.
Status: OK (same text), DIFF (different), NOT VERIFIABLE (the value is not saved in any derived file; the
reason is given). Results are printed and written to check/verification_results.csv.

The statistics use the same formulas as the notebooks and scripts named in the 'source' column; where the
manuscript value has no script in this package, the source says so.

Usage: python check/verify_manuscript_numbers.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code"))
import paths  # noqa: E402
from vehicle_ownership_covariate import rank_partial_corr  # noqa: E402

der = paths.der
WORLD_POP = 7830089931
results = []


def check(item, where, paper, value, fmt, source, note=""):
    got = fmt(value) if value is not None else ""
    status = "OK" if got == paper else "DIFF"
    results.append(dict(item=item, where=where, manuscript=paper, recomputed=got, status=status,
                        source=source, note=note))


def not_verifiable(item, where, paper, reason):
    results.append(dict(item=item, where=where, manuscript=paper, recomputed="", status="NOT VERIFIABLE",
                        source="", note=reason))


f0 = lambda v: f"{v:.0f}"
f1 = lambda v: f"{v:.1f}"
f2 = lambda v: f"{v:.2f}"
f3 = lambda v: f"{v:.3f}"
signed1 = lambda v: f"{v:+.1f}"
usd100 = lambda v: f"${round(v, -2):,.0f}"
usd1000 = lambda v: f"${round(v, -3):,.0f}"
int_comma = lambda v: f"{v:,.0f}"

# ---------------------------------------------------------------- Table 1, abstract, Results
pt = pd.read_csv(der("population_by_macroregion_traveltime.csv"))
g = pt.groupby("threshold_min")["population"].sum()
table1 = {1: ("1.24", "15.8"), 5: ("2.97", "38.0"), 10: ("4.05", "51.7"), 15: ("4.72", "60.3"),
          30: ("5.81", "74.2"), 45: ("6.36", "81.2"), 90: ("7.12", "91.0"), 120: ("7.36", "94.1"),
          180: ("7.52", "96.0")}
for t, (pb, sh) in table1.items():
    check(f"Population within {t} min (billion)", "Table 1", pb, g[t] / 1e9, f2, "population_per_travel_time.py")
    check(f"Share within {t} min (%)", "Table 1 / abstract / Fig. 3B", sh, 100 * g[t] / WORLD_POP, f1,
          "population_per_travel_time.py; statistics.ipynb")
not_verifiable("World population 2020 (billion)", "Table 1 caption, Methods", "7.83",
               "hard-coded constant 7,830,089,931 in the notebooks; see the raster-sum check in the README")

# ---------------------------------------------------------------- regional means (Fig. 1B, Results, Table S3)
mt = pd.read_csv(der("macroregion_traveltime.csv")).set_index("region")["travel_time"]
pr = pd.read_csv(der("population_by_macroregion.csv")).set_index("region")["population"]
for r, v in {"Western Europe": "2.2", "Southern Europe": "4.1", "South-Eastern Asia": "8.0", "Central Asia": "85.2",
             "Northern Africa": "61.7", "Southern Africa": "56.8", "Eastern Europe": "13.0",
             "Northern Europe": "12.0", "Southern Asia": "47.3"}.items():
    check(f"Mean travel time, {r} (min)", "Results, Fig. 1B", v, mt[r], f1, "regions_travel_time.py")
check("Ratio longest/shortest regional mean", "Results ('almost 40-fold')", "39", mt.max() / mt.min(), f0,
      "regions_travel_time.py")
check("Population of Southern Asia (billion)", "Results", "1.94", pr["Southern Asia"] / 1e9, f2,
      "population_regions.py")

# ---------------------------------------------------------------- Fig. 5 and quadrants (gdpAnalysis.ipynb)
reg = pd.read_csv(der("macroregion_pop_gdp_tt_average.csv")).set_index("region")
r_sp, p_sp = stats.spearmanr(reg["gdp_pc"], reg["time"])
check("Spearman r, GDP vs mean TT (n=17)", "Results", "-0.39", r_sp, f2, "statistics.ipynb / gdpAnalysis.ipynb")
check("Spearman p, GDP vs mean TT", "Results", "0.125", p_sp, f3, "statistics.ipynb")
w = reg["population"] / reg["population"].sum()
gm, tm = (w * reg["gdp_pc"]).sum(), (w * reg["time"]).sum()
r_wp = (w * (reg["gdp_pc"] - gm) * (reg["time"] - tm)).sum() / np.sqrt(
    (w * (reg["gdp_pc"] - gm) ** 2).sum() * (w * (reg["time"] - tm) ** 2).sum())
check("Population-weighted Pearson r", "Results", "-0.45", r_wp, f2, "statistics.ipynb")
quad = {"South-Eastern Asia": ("8", "$9,900"), "Middle Africa": ("11", "$2,300"), "Eastern Africa": ("25", "$1,700"),
        "Central Asia": ("85", "$9,800"), "Northern Africa": ("62", "$8,300"), "Southern Asia": ("47", "$5,300"),
        "Western Africa": ("32", "$3,400"), "Eastern Asia": ("34", "$15,600"), "Western Asia": ("49", "$20,200")}
for r, (tt, gd) in quad.items():
    check(f"Quadrant TT, {r} (min)", "Results, quadrants", tt, reg.loc[r, "time"], f0, "gdpAnalysis.ipynb")
    check(f"Quadrant GDP per capita, {r}", "Results, quadrants", gd, reg.loc[r, "gdp_pc"], usd100,
          "gdpAnalysis.ipynb")
adv = reg.loc[["Western Europe", "Northern Europe", "Northern America", "Southern Europe"]]
check("Double advantage, TT range (min)", "Results", "2--20",
      (adv["time"].min(), adv["time"].max()), lambda v: f"{v[0]:.0f}--{v[1]:.0f}", "gdpAnalysis.ipynb")
check("Double advantage, GDP range", "Results", "29,000--42,000", (adv["gdp_pc"].min(), adv["gdp_pc"].max()),
      lambda v: f"{round(v[0], -3):,.0f}--{round(v[1], -3):,.0f}", "gdpAnalysis.ipynb")
dd = reg[(reg["gdp_pc"] < 10_000) & (reg["time"] > 30)]
check("Double-disadvantage regions", "Results, Fig. 5A",
      "Central Asia, Northern Africa, Southern Asia, Western Africa", sorted(dd.index), lambda v: ", ".join(v),
      "gdpAnalysis.ipynb")
check("Double-disadvantage population (billion)", "Abstract, Results", "2.67", dd["population"].sum() / 1e9, f2,
      "gdpAnalysis.ipynb")
check("Double-disadvantage share of world population (%)", "Results", "34",
      100 * dd["population"].sum() / WORLD_POP, f0, "gdpAnalysis.ipynb")
check("Western Africa + Southern Asia (billion)", "Results, climate", "2.35",
      reg.loc[["Western Africa", "Southern Asia"], "population"].sum() / 1e9, f2, "population totals")
check("Share of double-disadvantage population in WA + SA (%)", "Results, climate", "88",
      100 * reg.loc[["Western Africa", "Southern Asia"], "population"].sum() / dd["population"].sum(), f0,
      "population totals")

# ---------------------------------------------------------------- Europe within 10 min (Fig. 3B)
fb = pd.read_csv(der("fig2b.csv"))
eu10 = fb[(fb["continent"] == "Europe") & (fb["threshold_min"] == 10)]["rel_pop"].iloc[0]
check("Europe, share within 10 min (%)", "Results ('over 85%')", ">85", eu10,
      lambda v: ">85" if v > 85 else f"{v:.1f}", "Figure3.ipynb (fig2b.csv)")

# ---------------------------------------------------------------- Fig. 6 (Figure4.ipynb)
px = pd.read_csv(der("travel_socio_eco_class.csv"), usecols=["travel_time", "population", "income_group"])
pct = {}
for grp, gg in px.groupby("income_group"):
    tot = gg["population"].sum()
    pct[grp] = {t: 100 * gg[gg["travel_time"] <= t]["population"].sum() / tot for t in table1}
check("High income, share within 10 min (%)", "Results, Fig. 6", "70.1", pct["High"][10], f1, "Figure4.ipynb")
check("Low income, share within 10 min (%)", "Results, Fig. 6", "56.8", pct["Low"][10], f1, "Figure4.ipynb")
check("Gap high - low at 10 min (pp)", "Results, Fig. 6 caption", "13.4", pct["High"][10] - pct["Low"][10], f1,
      "Figure4.ipynb")
gaps = {t: pct["High"][t] - pct["Low"][t] for t in table1}
check("Gap high - low at 5 min (pp)", "Abstract, Results", "13.6", gaps[5], f1, "Figure4.ipynb")
check("Threshold with the widest gap (min)", "Results", "5", max(gaps, key=gaps.get), str, "Figure4.ipynb")
check("Gap at 180 min (pp)", "Results ('approaching zero')", "~0", gaps[180],
      lambda v: "~0" if abs(v) < 1 else f"{v:.1f}", "Figure4.ipynb")

# ---------------------------------------------------------------- Table S1, urban-rural (urban_rural_gradient.py)
ur = pd.read_csv(der("urban_rural_traveltime_by_macroregion.csv")).set_index("region")
s1 = {"Central Asia": ("53.4", "67.2", "+13.8"), "Western Africa": ("17.0", "28.9", "+11.8"),
      "Western Asia": ("32.9", "44.4", "+11.4"), "Northern America": ("7.6", "5.3", "-2.3"),
      "Northern Europe": ("4.8", "2.9", "-1.9"), "Western Europe": ("3.3", "2.2", "-1.2")}
for r, (u, ru, gp) in s1.items():
    check(f"Urban TT, {r}", "Table S1", u, ur.loc[r, "urban_mean_tt"], f1, "urban_rural_gradient.py")
    check(f"Rural TT, {r}", "Table S1", ru, ur.loc[r, "rural_mean_tt"], f1, "urban_rural_gradient.py")
    check(f"Gap, {r}", "Table S1", gp, ur.loc[r, "gap_rural_minus_urban"], signed1, "urban_rural_gradient.py")
for r in ["Central Asia", "Western Africa", "Western Asia", "Eastern Africa", "Northern Africa"]:
    check(f"Rural minus urban in 7--14 min, {r}", "Results, urbanisation", "yes",
          ur.loc[r, "gap_rural_minus_urban"], lambda v: "yes" if 7 <= round(v) <= 14 else f"no ({v:.1f})",
          "urban_rural_gradient.py")
for r in ["Northern America", "Northern Europe", "Western Europe"]:
    check(f"Urban minus rural in 1--2 min, {r}", "Results, urbanisation", "yes",
          -ur.loc[r, "gap_rural_minus_urban"], lambda v: "yes" if 1 <= round(v) <= 2 else f"no ({v:.1f})",
          "urban_rural_gradient.py")
not_verifiable("Global urban / rural / gap (min)", "Results, Table S1", "21.0 / 23.1 / +2.2",
               "printed by urban_rural_gradient.py but not written to its CSV (regional rows only)")

# ---------------------------------------------------------------- Table S2 (climate_stratification_1km.py)
kg = pd.read_csv(der("koppen_stratified_stats_1km.csv")).set_index("climate_group")
s2 = {"Tropical (A)": ("2.33", "12.9", "0.57"), "Arid (B)": ("1.41", "47.7", "0.46"),
      "Temperate (C)": ("2.81", "18.4", "0.68"), "Continental (D)": ("1.03", "15.2", "0.69"),
      "Polar (E)": ("0.01", "48.3", "0.51")}
for c, (p, t, gi) in s2.items():
    check(f"Population, {c} (billion)", "Table S2", p, kg.loc[c, "total_population"] / 1e9, f2,
          "climate_stratification_1km.py")
    check(f"Mean TT, {c}", "Table S2", t, kg.loc[c, "pop_weighted_mean_tt"], f1, "climate_stratification_1km.py")
    check(f"Gini, {c}", "Table S2", gi, kg.loc[c, "gini"], f2, "climate_stratification_1km.py")
arid = kg.loc["Arid (B)", "pop_weighted_mean_tt"]
others = kg.loc[["Tropical (A)", "Temperate (C)", "Continental (D)"], "pop_weighted_mean_tt"]
check("Arid vs A/C/D, ratio range", "Results, climate", "2.6 to 3.7", (arid / others.max(), arid / others.min()),
      lambda v: f"{v[0]:.1f} to {v[1]:.1f}", "climate_stratification_1km.py")
not_verifiable("Climate composition (N Africa 78% arid, C Asia 77%, W Africa 72% tropical, S Asia 67%)",
               "Results, climate", "78 / 77 / 72 / 67",
               "printed by macroregion_climate_composition_1km.py, not written to a file (see README check of the "
               "heavy step)")
not_verifiable("0.5 deg vs 1 km reassigns up to ~40% of population", "Methods", "~40%",
               "no script in the repository (0.5 deg tables shipped as *_0p5deg.csv, producer missing)")

# ---------------------------------------------------------------- climate covariates (Fig. S3)
thr = pd.read_csv(der("macroregion_pop_gdp_traveltime.csv"))
r180 = thr[thr["threshold_min"] == 180].set_index("region")
clim = pd.read_csv(der("macroregion_pop_gdp_tt_climate.csv")).set_index("region")
regions = sorted(r180.index)
pre = clim.loc[regions, "annual_precip_mm"]
r, p = stats.spearmanr(pre, r180.loc[regions, "time"])
check("Spearman r, precipitation vs TT", "Results, Fig. S3", "-0.77", r, f2, "figure_S3_S4_covariate_scatters.py")
check("Spearman p < 0.001, precipitation vs TT", "Results", "<0.001", p, lambda v: "<0.001" if v < 0.001 else f3(v),
      "figure_S3_S4_covariate_scatters.py")
r, p = stats.spearmanr(pre, r180.loc[regions, "gdp_pc"])
check("Spearman r, precipitation vs GDP", "Results, Fig. S3", "-0.04", r, f2, "figure_S3_S4_covariate_scatters.py")
check("Spearman p, precipitation vs GDP", "Results", "0.89", p, f2, "figure_S3_S4_covariate_scatters.py")


def partial_two(x, y, z1, z2):
    """Rank-residual partial correlation with two controls (Methods); no script in the repository."""
    rk = lambda a: stats.rankdata(a)
    Z = np.column_stack([np.ones(len(x)), rk(z1), rk(z2)])
    res = lambda a: rk(a) - Z @ np.linalg.lstsq(Z, rk(a), rcond=None)[0]
    rr = stats.pearsonr(res(x), res(y))[0]
    df = len(x) - 2 - 2
    tt_ = rr * np.sqrt(df / (1 - rr ** 2))
    return rr, 2 * (1 - stats.t.cdf(abs(tt_), df))


for label, gdp_src in [("whole-region GDP (Fig. 5 values)", reg.loc[regions, "gdp_pc"]),
                       ("GDP of pixels <= 180 min (Table S3 values)", r180.loc[regions, "gdp_pc"])]:
    rr, pp = partial_two(gdp_src.values, reg.loc[regions, "time"].values, clim.loc[regions, "mean_annual_temp_C"],
                         clim.loc[regions, "annual_precip_mm"])
    check(f"Partial r GDP-TT | temperature, precipitation [{label}]", "Results, climate", "-0.51 (p=0.035)",
          (rr, pp), lambda v: f"{v[0]:.2f} (p={v[1]:.3f})",
          "NO SCRIPT in repository; recomputed here (rank-residual, Methods)")

# ---------------------------------------------------------------- vehicles (Table S3, Fig. S4)
veh = json.load(open(der("vehicles_per_1000_by_macroregion.json")))
vr = sorted(r for r in r180.index if r in veh)
vp = [veh[r]["veh_per_1000"] for r in vr]
tt_v = r180.loc[vr, "time"].values
gdp_v = r180.loc[vr, "gdp_pc"].values
r, p = stats.spearmanr(vp, tt_v)
check("Spearman r, vehicles vs TT", "Results, Fig. S4", "-0.50 (p=0.042)", (r, p),
      lambda v: f"{v[0]:.2f} (p={v[1]:.3f})", "vehicle_ownership_covariate.py")
r, p = stats.spearmanr(vp, gdp_v)
check("Spearman r, vehicles vs GDP", "Results, Fig. S4", "0.94", r, f2, "vehicle_ownership_covariate.py")
r, p = stats.spearmanr(gdp_v, tt_v)
check("Unconditional Spearman GDP-TT in the vehicle analysis", "Results ('versus the unconditional')",
      "-0.39 (p=0.125)", (r, p), lambda v: f"{v[0]:.2f} (p={v[1]:.3f})", "vehicle_ownership_covariate.py",
      "the vehicle script uses GDP of pixels <= 180 min, not the whole-region GDP of Fig. 5")
pr_ = rank_partial_corr(gdp_v, tt_v, vp)
df_ = len(vr) - 3
pp_ = 2 * (1 - stats.t.cdf(abs(pr_ * np.sqrt(df_ / (1 - pr_ ** 2))), df_))
check("Partial r GDP-TT | vehicles", "Results", "0.26 (p=0.33)", (pr_, pp_), lambda v: f"{v[0]:.2f} (p={v[1]:.2f})",
      "vehicle_ownership_covariate.py")
s3t = {"Eastern Africa": ("29", "1,696", "25.2"), "Middle Africa": ("45", "2,305", "10.7"),
       "Western Africa": ("55", "3,516", "32.0"), "Northern Africa": ("97", "8,572", "61.7"),
       "Southern Asia": ("145", "5,316", "47.3"), "Central Asia": ("175", "8,449", "85.2"),
       "Southern Africa": ("191", "11,302", "56.8"), "Western Asia": ("235", "16,357", "48.8"),
       "Eastern Asia": ("257", "15,684", "34.1"), "South America": ("351", "14,126", "15.5"),
       "South-Eastern Asia": ("410", "9,836", "8.0"), "Eastern Europe": ("429", "21,644", "13.0"),
       "Oceania": ("565", "28,456", "33.8"), "Northern Europe": ("608", "39,100", "12.0"),
       "Western Europe": ("672", "41,483", "2.2"), "Southern Europe": ("733", "29,216", "4.1"),
       "Northern America": ("854", "36,062", "19.1")}
for r_, (v_, gd, tt_paper) in s3t.items():
    check(f"Vehicles per 1,000, {r_}", "Table S3", v_, veh[r_]["veh_per_1000"], f0, "vehicle_ownership_covariate.py")
    check(f"GDP per capita, {r_}", "Table S3", gd, r180.loc[r_, "gdp_pc"], int_comma,
          "population_gdp_travel_time.py (threshold 180 row)")
    check(f"Mean TT, {r_}", "Table S3", tt_paper, r180.loc[r_, "time"], f1,
          "population_gdp_travel_time.py (threshold 180 row)")
for r_ in ["Southern Asia", "Western Africa", "Eastern Africa", "Middle Africa", "Northern Africa", "Central Asia"]:
    a, b = reg.loc[r_, "gdp_pc"], r180.loc[r_, "gdp_pc"]
    if f"{round(a, -2):,.0f}" != f"{round(b, -2):,.0f}":
        results.append(dict(item=f"GDP per capita, {r_}: Results text vs Table S3", where="Results vs Table S3",
                            manuscript="", recomputed=f"text {a:,.0f} / table {b:,.0f}", status="INCONSISTENT",
                            source="", note="Fig. 5/text use whole-region GDP per capita; Table S3 uses pixels "
                                            "<= 180 min"))

# ---------------------------------------------------------------- Table S4 (ssp_2050_projection.py)
ssp = pd.read_csv(der("ssp2050_macroregion_stats.csv")).set_index("region")
for col, v in [("mean_tt_2020", "21.8"), ("mean_tt_SSP1_2050", "22.3"), ("mean_tt_SSP3_2050", "22.7")]:
    check(f"Global pop-weighted TT, {col}", "Table S4, Results", v, ssp.loc["GLOBAL", col], f1,
          "ssp_2050_projection.py")
three = ["Southern Asia", "Northern Africa", "Central Asia"]
for col, v in [("total_pop_2020_B", "2.14"), ("total_pop_SSP1_2050_B", "2.58"), ("total_pop_SSP3_2050_B", "2.87")]:
    check(f"Double-disadvantage population, {col}", "Table S4, Results", v, ssp.loc[three, col].sum(), f2,
          "sum of three regions in ssp_2050_projection.py output; classification code MISSING")
not_verifiable("Share within 10 / 30 min, 2020 / SSP1 / SSP3", "Table S4, Results",
               "53.9/52.8/52.0; 77.3/76.7/76.3",
               "printed by ssp_2050_projection.py, not written to its CSV")
not_verifiable("2050 double-disadvantage classification (median thresholds)", "Results, Methods",
               "3 regions in both pathways", "no script in the repository")

# ---------------------------------------------------------------- not in derived data
not_verifiable("Global population-weighted mean TT (min)", "Results, Fig. 2", "21.7",
               "computed from native rasters by statistics.ipynb (see README check)")
not_verifiable("Unweighted spatial mean, native to 100 km", "Fig. S2 caption", "21.4 to 30.9",
               "no script in the repository (Fig. S2)")

res = pd.DataFrame(results)
res.to_csv(os.path.join(HERE, "verification_results.csv"), index=False)
pd.set_option("display.width", 250, "display.max_colwidth", 70, "display.max_rows", 500)
print(res[["status", "where", "item", "manuscript", "recomputed"]].to_string(index=False))
print()
print(res["status"].value_counts().to_string())
