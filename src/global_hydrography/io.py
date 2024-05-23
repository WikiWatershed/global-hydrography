'''
Global Hydrography functions for fetching and saving data.
'''

# Imports


# HydroBASINS Identifier & Region (Section 3.1 in Tech Docs)
hybas_region_dict = {
    'af': 'Africa',
    'ar': 'North American Arctic',
    'as': 'Central and South-East Asia',
    'au': 'Australia and Oceania',
    'eu': 'Europe and Middle East',
    'gr': 'Greenland',
    'na': 'North America and Caribbean sa South America',
    'si': 'Siberia',
}

def get_tdxhydro():
    return 1