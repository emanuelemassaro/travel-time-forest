import paths  # input and output locations, from config.yaml
import rasterio
import my_utils as mu

# File paths
pop_fp = paths.inp("population")
tt_fp = paths.inp("tt_gfc_50")
shapefile_fp = paths.inp("macroregions")

# Open rasters
with rasterio.open(pop_fp) as pop_src, rasterio.open(tt_fp) as tt_src:
    df = mu.count_cumulative_population_by_thresholds(pop_src, tt_src, shapefile_fp)

# Save results
df.to_csv(paths.der("population_by_macroregion_traveltime.csv"), index=False)
