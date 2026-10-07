import paths  # input and output locations, from config.yaml
import rasterio
import numpy as np
import pandas as pd
import geopandas as gpd
from rasterio.mask import mask


pop_fp = paths.inp("population")
pop_src = rasterio.open(pop_fp)

shapefile_fp = paths.inp("macroregions")
gdf = gpd.read_file(shapefile_fp)
gdf = gdf.to_crs(pop_src.crs)

results = []
for idx, region in gdf.iterrows():
    region_name = region['custom_reg'] if 'custom_reg' in region else f'region_{idx}'
    geom = [region.geometry]
    # Mask population and travel time rasters with the region
    pop_masked, _ = mask(pop_src, geom, crop=True)
    pop_masked[pop_masked<0] = 0
    tot_pop = np.nansum(pop_masked)
    results.append({
        'region': region_name,
        'population': int(tot_pop)
    })

df = pd.DataFrame(results)
df.to_csv(paths.der("population_by_macroregion.csv"), index=False)
