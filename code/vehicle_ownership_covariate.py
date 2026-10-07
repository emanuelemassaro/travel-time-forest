"""
Vehicle ownership as a covariate on the GDP-travel time relationship
(coauthor feedback, 2026-08-27: "Travel time to forest is not only
determined by the transport network, it is also constrained by access
to vehicles. Could you integrate vehicle ownership per 1000
inhabitants ... into your analysis instead of or on top of GDP?").

Data:
  - Registered vehicles per country: WHO Global Health Observatory,
    indicator RS_194 ("Number of registered vehicles"; includes
    motorcycles/two- and three-wheelers, not only cars), via the GHO
    OData API (https://ghoapi.azureedge.net/api/RS_194). For each
    country, the most recent available year is used (predominantly
    2016; range 2007-2017; 160 of 161 countries with a value could be
    matched to a population estimate).
  - Country population for the matching year: World Bank SP.POP.TOTL.
  - Country-to-macroregion mapping: UN M49 standard area classification
    (via iso3166 codes), same crosswalk used in
    Codes/climate_stratification_1km.py and
    Codes/macroregion_climate_composition_1km.py.

Vehicles per 1,000 inhabitants are aggregated to each of the 17
macroregions as a population-weighted mean. The correlation with
travel time and GDP per capita, and the partial correlation between
GDP and travel time controlling for vehicle ownership, are computed
using the same macroregion-level travel time and GDP per capita values
as the existing GDP-travel time analysis
(Data/Output/macroregion_pop_gdp_traveltime.csv, threshold=180 row,
i.e. the whole-region unweighted mean -- see main text Methods,
"Regional analysis and statistics", for why this is the convention
used for the macroregion-level statistic).

NOTE: this script assumes country_to_macro.json (UN M49 numeric
code -> macroregion) and unm49_by_code.json (UN M49 code -> name/
iso3166/parent) already exist, as built interactively earlier in this
session (see climate_stratification_1km.py's crosswalk-building code,
not duplicated here for brevity). Re-run that crosswalk-building step
first if these files are not present in Data/Output/.
"""
import paths  # input and output locations, from config.yaml
import csv
import json
import os
import sys

import numpy as np
from scipy import stats

BASE = os.path.join(os.path.dirname(__file__), "..")


def fetch_gho_indicator(code):
    import urllib.request
    url = f"https://ghoapi.azureedge.net/api/{code}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["value"]


def fetch_wb_population(date_range="2007:2017"):
    import urllib.request
    url = (f"https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL"
           f"?format=json&per_page=20000&date={date_range}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)[1]


def rank_partial_corr(x, y, z):
    rx, ry, rz = stats.rankdata(x), stats.rankdata(y), stats.rankdata(z)
    rxz = stats.pearsonr(rx, rz)[0]
    ryz = stats.pearsonr(ry, rz)[0]
    rxy = stats.pearsonr(rx, ry)[0]
    return (rxy - rxz * ryz) / np.sqrt((1 - rxz**2) * (1 - ryz**2))


def main():
    records = fetch_gho_indicator("RS_194")
    by_country = {}
    for r in records:
        iso3, year, val = r["SpatialDim"], r["TimeDim"], r["NumericValue"]
        if iso3 is None or val is None:
            continue
        if iso3 not in by_country or year > by_country[iso3][0]:
            by_country[iso3] = (year, val)

    wb_pop = fetch_wb_population()
    pop_lookup = {(r["countryiso3code"], int(r["date"])): r["value"]
                  for r in wb_pop if r["value"] is not None}

    veh_per_1000 = {}
    for iso3, (year, veh_count) in by_country.items():
        pop = pop_lookup.get((iso3, year))
        if pop:
            veh_per_1000[iso3] = {"year": year, "vehicles": veh_count,
                                   "population": pop, "veh_per_1000": veh_count / pop * 1000}

    by_code = json.load(open(paths.der("unm49_by_code.json")))
    country_to_macro = json.load(open(paths.der("country_to_macro.json")))
    iso3_to_macro = {node["iso3166"]: country_to_macro[code]
                      for code, node in by_code.items()
                      if node.get("iso3166") and code in country_to_macro}

    from collections import defaultdict
    macro_vals = defaultdict(list)
    for iso3, rec in veh_per_1000.items():
        macro = iso3_to_macro.get(iso3)
        if macro:
            macro_vals[macro].append((rec["veh_per_1000"], rec["population"]))

    results = {}
    for macro, vals in macro_vals.items():
        total_pop = sum(p for _, p in vals)
        wtd = sum(v * p for v, p in vals) / total_pop
        results[macro] = {"n_countries": len(vals), "veh_per_1000": wtd, "sample_pop": total_pop}

    out_json = paths.der("vehicles_per_1000_by_macroregion.json")
    json.dump(results, open(out_json, "w"), indent=1)

    rows = list(csv.DictReader(open(paths.der("macroregion_pop_gdp_traveltime.csv"))))
    rows180 = {r["region"]: r for r in rows if r["threshold_min"] == "180"}
    regions = sorted(r for r in rows180 if r in results)
    tt = [float(rows180[r]["time"]) for r in regions]
    gdp = [float(rows180[r]["gdp_pc"]) for r in regions]
    vehp = [results[r]["veh_per_1000"] for r in regions]

    r_tt_veh, p_tt_veh = stats.spearmanr(vehp, tt)
    r_gdp_veh, p_gdp_veh = stats.spearmanr(vehp, gdp)
    r_gdp_tt, p_gdp_tt = stats.spearmanr(gdp, tt)
    partial_r = rank_partial_corr(gdp, tt, vehp)
    n, k = len(regions), 1
    df = n - 2 - k
    t = partial_r * np.sqrt(df / (1 - partial_r**2))
    partial_p = 2 * (1 - stats.t.cdf(abs(t), df))

    print(f"Spearman(vehicles/1000, travel time): r={r_tt_veh:.3f}, p={p_tt_veh:.4f}")
    print(f"Spearman(vehicles/1000, GDP per capita): r={r_gdp_veh:.3f}, p={p_gdp_veh:.4f}")
    print(f"Spearman(GDP, TT) unconditional: r={r_gdp_tt:.3f}, p={p_gdp_tt:.4f}")
    print(f"Partial Spearman(GDP, TT | vehicles/1000): r={partial_r:.3f}, p={partial_p:.4f}")


if __name__ == "__main__":
    main()
