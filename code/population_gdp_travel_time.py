import paths  # input and output locations, from config.yaml
import rasterio
import my_utils as mu # type: ignore


# File paths
pop_fp = paths.inp("population")
tt_fp = paths.inp("tt_gfc_50")
gdp_fp = paths.der("rasters/GDP_PPP_2015_compressed.tif")
shapefile_fp = paths.inp("macroregions")


# Open rasters
with rasterio.open(pop_fp) as pop_src, rasterio.open(tt_fp) as tt_src, rasterio.open(gdp_fp) as gdp_src:
    #df, df1 = mu.gdp_travel_time(pop_src, tt_src, gdp_src, shapefile_fp)
    df2 = mu.get_pixel_level_data_windowed(pop_src, tt_src, gdp_src)

#df.to_csv(paths.der("macroregion_pop_gdp_traveltime.csv"), index=False)
#df1.to_csv(paths.der("macroregion_pop_gdp_tt_average.csv"), index=False)
df2.to_csv(paths.der("travel_socio_eco_class.csv"), index=False)
