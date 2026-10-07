from palettable.cartocolors.qualitative import Safe_3, Antique_5, Vivid_7
from palettable.cubehelix import cubehelix3_16

CONTINENT_COLORS = {
    'Asia': Antique_5.hex_colors[0],
    'Africa': Safe_3.hex_colors[2],
    'Europe': cubehelix3_16.hex_colors[3],
    'America': Antique_5.hex_colors[3],
    'Oceania': Vivid_7.hex_colors[5]
}

REGION_TO_CONTINENT = {
    'Central Asia': 'Asia',
    'Eastern Africa': 'Africa',
    'Eastern Asia': 'Asia',
    'Eastern Europe': 'Europe',
    'Middle Africa': 'Africa',
    'Northern Africa': 'Africa',
    'Northern America': 'America',
    'Northern Europe': 'Europe',
    'Oceania': 'Oceania',
    'South America': 'America',
    'South-Eastern Asia': 'Asia',
    'Southern Africa': 'Africa',
    'Southern Asia': 'Asia',
    'Southern Europe': 'Europe',
    'Western Africa': 'Africa',
    'Western Asia': 'Asia',
    'Western Europe': 'Europe'
}
