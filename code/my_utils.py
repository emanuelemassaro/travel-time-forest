# my_utils.py
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.transform import Affine
from skimage.measure import block_reduce # type: ignore


import geopandas as gpd
import pandas as pd
from rasterio.features import geometry_mask
from rasterio.mask import mask
from shapely.geometry import box
from rasterio.windows import from_bounds

def align_rasters(pop_src, tt_src, invalid_tt_val=255):
    """
    Aligns population and travel time rasters to their overlapping extent.

    Args:
        pop_src (rasterio.io.DatasetReader): Population raster.
        tt_src (rasterio.io.DatasetReader): Travel time raster.
        invalid_tt_val (int): Value representing invalid travel time (default 255).

    Returns:
        tuple: Aligned (population, travel_time) numpy arrays.
    """
    assert pop_src.crs == tt_src.crs, "CRS do not match"

    pop_bounds = pop_src.bounds
    tt_bounds = tt_src.bounds
    
    overlap_bounds = (
        max(pop_bounds.left, tt_bounds.left),
        max(pop_bounds.bottom, tt_bounds.bottom),
        min(pop_bounds.right, tt_bounds.right),
        min(pop_bounds.top, tt_bounds.top)
    )

    pop_window = from_bounds(*overlap_bounds, transform=pop_src.transform)
    tt_window = from_bounds(*overlap_bounds, transform=tt_src.transform)

    population = pop_src.read(1, window=pop_window)
    population[population<0] = 0
    population[(population > 0) & (population <= 1)] = 1
    travel_time = tt_src.read(1, window=tt_window)

    travel_time = np.where(travel_time == invalid_tt_val, np.nan, travel_time)

    min_rows = min(population.shape[0], travel_time.shape[0])
    min_cols = min(population.shape[1], travel_time.shape[1])

    population = population[:min_rows, :min_cols]
    travel_time = travel_time[:min_rows, :min_cols]

    return population, travel_time

def compute_block_mean(array, block_size):
    return block_reduce(array, block_size, np.nanmean)

def compute_block_sum(array, block_size):
    return block_reduce(array, block_size, np.nansum)

def compute_block_weighted_mean(tt_array, pop_array, block_size):
    """
    Compute population-weighted travel time average over blocks.

    Args:
        tt_array (ndarray): Travel time array.
        pop_array (ndarray): Population array.
        block_size (tuple): Size of the block (rows, cols).

    Returns:
        ndarray: Block-wise population-weighted travel time average.
    """
    A = tt_array * pop_array
    numerator = block_reduce(A, block_size, np.nansum)
    del(A)
    denominator = block_reduce(pop_array, block_size, np.nansum)
    with np.errstate(divide='ignore', invalid='ignore'):
        tt_mean_block = numerator / denominator
        tt_mean_block = np.where(denominator == 0, np.nan, tt_mean_block)
    return tt_mean_block

def get_new_transform(orig_transform, block_size):
    """
    Compute the new transform for a block-reduced raster.

    Args:
        orig_transform (Affine): Original affine transform.
        block_size (tuple): Block size used for reduction.

    Returns:
        Affine: New affine transform.
    """
    return Affine(
        orig_transform.a * block_size[1],
        orig_transform.b,
        orig_transform.c,
        orig_transform.d,
        orig_transform.e * block_size[0],
        orig_transform.f
    )
def save_raster(output_path, array, transform, crs, nodata=-9999):
    """
    Save a numpy array as a GeoTIFF with a defined nodata value.

    Args:
        output_path (str): File path to save the raster.
        array (ndarray): Raster data.
        transform (Affine): Affine transform.
        crs: Coordinate reference system.
        nodata: Value representing no data (default -9999).
    """
    # Replace np.nan with nodata value
    array_to_save = np.where(np.isnan(array), nodata, array)

    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype=array.dtype,
        crs=crs,
        transform=transform,
        nodata=nodata
    ) as dst:
        dst.write(array_to_save, 1)



def count_cumulative_population_by_thresholds(
    pop_src, tt_src, shapefile_path,
    thresholds=[1, 5, 10, 15, 30, 45, 90, 120, 180],
    invalid_tt_val=255
):
    # Load shapefile and reproject to match raster
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.to_crs(pop_src.crs)

    results = []

    for idx, region in gdf.iterrows():
        region_name = region['custom_reg'] if 'custom_reg' in region else f'region_{idx}'
        geom = [region.geometry]

        # Mask population and travel time rasters with the region
        pop_masked, _ = mask(pop_src, geom, crop=True)
        tt_masked, _ = mask(tt_src, geom, crop=True)

        pop_masked[pop_masked<0] = 0

        pop_arr = pop_masked[0]
        tt_arr = tt_masked[0]

        # Mask invalid travel times
        tt_arr = np.where(tt_arr == invalid_tt_val, np.nan, tt_arr)

        # Calculate cumulative population for each threshold
        for t in thresholds:
            mask_t = (tt_arr <= t)
            total_pop = np.nansum(pop_arr[mask_t])
            results.append({
                'region': region_name,
                'threshold_min': t,
                'population': int(total_pop)
            })
            print(f'Population living in {t} to forest in {region_name} is: {total_pop}')

    return pd.DataFrame(results)

def compute_block_weighted_mean_manual(tt_array, pop_array, block_size_px, valid_mask=None):
    # Convert travel time to float to allow NaNs
    tt_array = tt_array.astype(np.float32)
    tt_array[tt_array == 255] = np.nan  # Mask oceans or invalid cells

    height, width = tt_array.shape
    height_blocks = height // block_size_px
    width_blocks = width // block_size_px
    weighted_tt = np.full((height_blocks, width_blocks), np.nan, dtype=np.float32)

    for i in range(height_blocks):
        for j in range(width_blocks):
            r0 = i * block_size_px
            c0 = j * block_size_px

            tt_block = tt_array[r0:r0+block_size_px, c0:c0+block_size_px]
            pop_block = pop_array[r0:r0+block_size_px, c0:c0+block_size_px]

            # Round small positive population values to 1
            pop_block = pop_block.copy()  # avoid modifying original array
            pop_block[(pop_block > 0) & (pop_block < 1)] = 1

            # Optional valid mask
            if valid_mask is not None:
                mask_block = valid_mask[r0:r0+block_size_px, c0:c0+block_size_px]
                tt_block = tt_block[mask_block]
                pop_block = pop_block[mask_block]

            # Mask invalid travel times
            valid = ~np.isnan(tt_block)
            if not np.any(valid):
                continue  # skip block if all tt are NaN

            tt_block = tt_block[valid]
            pop_block = pop_block[valid]

            total_pop = np.nansum(pop_block)
            if total_pop >= 1:
                weighted_sum = np.nansum(tt_block * pop_block)
                weighted_tt[i, j] = weighted_sum / total_pop

    return weighted_tt



def compute_population_below_threshold_manual(tt_array, pop_array, block_size_px, threshold, valid_mask=None):
    """
    Conta la popolazione in ogni blocco 50x50 dove travel_time <= threshold.
    Imposta NaN se TUTTI i travel_time nel blocco sono np.nan (es. oceano).

    Args:
        tt_array (ndarray): Travel time array.
        pop_array (ndarray): Population array.
        block_size_px (int): Block size.
        threshold (float): Travel time threshold.
        valid_mask (ndarray or None): Optional mask.

    Returns:
        ndarray: 2D array of population counts.
    """
    height, width = tt_array.shape
    height_blocks = height // block_size_px
    width_blocks = width // block_size_px
    pop_count = np.full((height_blocks, width_blocks), np.nan, dtype=np.float32)

    for i in range(height_blocks):
        for j in range(width_blocks):
            r0 = i * block_size_px
            c0 = j * block_size_px

            tt_block = tt_array[r0:r0+block_size_px, c0:c0+block_size_px]
            pop_block = pop_array[r0:r0+block_size_px, c0:c0+block_size_px]

            if valid_mask is not None:
                mask_block = valid_mask[r0:r0+block_size_px, c0:c0+block_size_px]
                tt_block = tt_block[mask_block]
                pop_block = pop_block[mask_block]

            # ⛔ Se tutti i valori sono nan → blocco interamente invalido
            if np.all(np.isnan(tt_block)):
                continue

            valid_idx = (tt_block <= threshold) & (~np.isnan(tt_block))
            valid_pop = pop_block[valid_idx]
            valid_pop[(valid_pop > 0) & (valid_pop < 1)] = 1

            pop_count[i, j] = np.nansum(valid_pop)
    print(pop_count)

    return pop_count

def gdp_blocks(gdp_array, block_size_px):
    height, width = gdp_array.shape
    height_blocks = height // block_size_px
    width_blocks = width // block_size_px
    gdp_avg = np.full((height_blocks, width_blocks), np.nan, dtype=np.float32)

    for i in range(height_blocks):
        for j in range(width_blocks):
            r0 = i * block_size_px
            c0 = j * block_size_px

            gdp_block = gdp_array[r0:r0+block_size_px, c0:c0+block_size_px]
            gdp_avg[i, j] = np.nanmean(gdp_block)
    return gdp_avg



def gdp_travel_time(
    pop_src, tt_src, gdp_src, shapefile_path,
    thresholds=[1, 5, 10, 15, 30, 45, 90, 120, 180],
    invalid_tt_val=255
):
    # Load shapefile
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.to_crs(pop_src.crs)  # Ensure same CRS

    # Align the rasters
    from_bounds_overlap = (
        max(pop_src.bounds.left, tt_src.bounds.left),
        max(pop_src.bounds.bottom, tt_src.bounds.bottom),
        min(pop_src.bounds.right, tt_src.bounds.right),
        min(pop_src.bounds.top, tt_src.bounds.top)
    )
    
    
    # Crop shapes to raster extent
    results = []
    results1 = []
    for idx, region in gdf.iterrows():
        region_name = region['custom_reg'] if 'custom_reg' in region else f"region_{idx}"
        geom = [region.geometry]

        # Mask population and travel time
        pop_masked, _ = mask(pop_src, geom, crop=True)
        tt_masked, _ = mask(tt_src, geom, crop=True)
        gdf_masked, _ = mask(gdp_src, geom, crop=True)

        pop_masked = pop_masked[0]
        pop_masked[pop_masked<0]=0
        tt_masked = tt_masked[0]
        tt_masked = np.where(tt_masked == invalid_tt_val, np.nan, tt_masked)
        gdf_masked = gdf_masked[0]

        tt_mean = np.nanmean(tt_masked)
        pop_sum_region = np.nansum(pop_masked)
        gdp_sum_region = np.nansum(gdf_masked)
        gdp_pc_region = gdp_sum_region / pop_sum_region

        results1.append({
            'region': region_name,
            'population': int(pop_sum_region),
            'time': tt_mean,
            'gdp_avg': np.nanmean(gdf_masked),
            'gdp_tot': gdp_sum_region,
            'gdp_pc': gdp_pc_region
        })
        
        # Calculate cumulative population for each threshold
        for t in thresholds:
            mask_t = (tt_masked <= t)
            total_pop = np.nansum(pop_masked[mask_t])
            gdp_avg   = np.nanmean(gdf_masked[mask_t])
            gdp_tot   = np.nansum(gdf_masked[mask_t])
            gdp_pc    = gdp_tot / total_pop
            tt_avg    = np.nanmean(tt_masked[mask_t])
            results.append({
                'region': region_name,
                'threshold_min': t,
                'population': int(total_pop),
                'time': tt_avg,
                'gdp_avg': gdp_avg,
                'gdp_tot': gdp_tot,
                'gdp_pc': gdp_pc
            })
            print(f'Population living in {t} to forest in {region_name} is: {total_pop} with gdp: {gdp_avg}')

    return pd.DataFrame(results), pd.DataFrame(results1)




def classify_income(gdp):
    if gdp < 1095:
        return 'Low'
    elif gdp < 4255:
        return 'Lower-middle'
    elif gdp < 13205:
        return 'Upper-middle'
    else:
        return 'High'

def get_pixel_level_data_windowed(pop_src, tt_src, gdp_src, invalid_tt_val=255, stride=512):
    results = []

    for ji, window in tt_src.block_windows(1):
        # Read window
        pop = pop_src.read(1, window=window)
        tt = tt_src.read(1, window=window)
        gdp = gdp_src.read(1, window=window)

        # Clean
        pop[pop < 0] = 0
        tt = np.where(tt == invalid_tt_val, np.nan, tt)
        gdp[gdp < 0] = np.nan

        # GDP per capita
        with np.errstate(divide='ignore', invalid='ignore'):
            gdp_pc = np.where(pop > 0, gdp / pop, np.nan)

        # Filter valid
        mask = ~np.isnan(tt) & ~np.isnan(gdp_pc)
        if not np.any(mask):
            continue

        data = {
            'travel_time': tt[mask],
            'population': pop[mask],
            'gdp_pc': gdp_pc[mask]
        }
        df_chunk = pd.DataFrame(data)
        df_chunk['income_group'] = df_chunk['gdp_pc'].apply(classify_income)
        results.append(df_chunk)

    df_all = pd.concat(results, ignore_index=True)
    return df_all




def average_time(
    pop_src, tt_src, shapefile_path,
    invalid_tt_val=255
):
    # Load shapefile
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.to_crs(pop_src.crs)  # Ensure same CRS

    # Align the rasters
    from_bounds_overlap = (
        max(pop_src.bounds.left, tt_src.bounds.left),
        max(pop_src.bounds.bottom, tt_src.bounds.bottom),
        min(pop_src.bounds.right, tt_src.bounds.right),
        min(pop_src.bounds.top, tt_src.bounds.top)
    )

    tt_window = from_bounds(*from_bounds_overlap, transform=tt_src.transform)

    travel_time = tt_src.read(1, window=tt_window)

    # Replace invalid values
    travel_time = np.where(travel_time == invalid_tt_val, np.nan, travel_time)

    # Crop shapes to raster extent
    results = []

    # Crop shapes to raster extent
    results = []

    for idx, region in gdf.iterrows():
        region_name = region['custom_reg'] if 'custom_reg' in region else f"region_{idx}"
        geom = [region.geometry]

        # Mask population and travel time
        tt_masked, _ = mask(tt_src, geom, crop=True)

        tt_masked = tt_masked[0]
        tt_masked = np.where(tt_masked == invalid_tt_val, np.nan, tt_masked)
        tt_mean = np.nanmean(tt_masked)
        results.append({
            'region': region_name,           
            'travel_time': tt_mean
        })            

    return pd.DataFrame(results)


def compute_block_forest_area(tt_array, block_size_px):
    # Convert travel time to float to allow NaNs
    tt_array = tt_array.astype(np.float32)
    tt_array[tt_array == 255] = np.nan  # Mask oceans or invalid cells
    height, width = tt_array.shape
    height_blocks = height // block_size_px
    width_blocks = width // block_size_px
    area_tt = np.full((height_blocks, width_blocks), np.nan, dtype=np.float32)
    for i in range(height_blocks):
        for j in range(width_blocks):
            r0 = i * block_size_px
            c0 = j * block_size_px
            tt_block = tt_array[r0:r0+block_size_px, c0:c0+block_size_px]
            area_f = np.nansum(tt_block == 0)
            area_tt[i, j] = area_f 
    return area_tt