import paths  # input and output locations, from config.yaml
import xarray as xr
import rioxarray

# Convert total GDP PPP (30 arc-sec) → GeoTIFF for 2015
pathf = paths.inp("gdp_total_nc")
ds = xr.open_dataset(pathf)
data_2015 = ds['GDP_PPP'].sel(time='2015', method='nearest')
data_2015.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True)
data_2015.rio.write_crs("EPSG:4326", inplace=True)
data_2015.rio.to_raster(paths.der("rasters/GDP_PPP_2015.tif"))
print("Saved GDP_PPP_2015.tif")

# Convert GDP per capita PPP (5 arc-min) → GeoTIFF for 2015
pathf = paths.inp("gdp_pc_nc")
ds = xr.open_dataset(pathf)
data_2015 = ds['GDP_per_capita_PPP'].sel(time='2015', method='nearest')
data_2015.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True)
data_2015.rio.write_crs("EPSG:4326", inplace=True)
data_2015.rio.to_raster(paths.der("rasters/GDP_per_capita_PPP_2015.tif"), compress="LZW")
print("Saved GDP_per_capita_PPP_2015.tif")
