from vehi_rout.utils.helper_utils import get_osrm_data
import pandas as pd
import numpy as np
import os

def update_master_gps(master_gps_path, new_gps_path):
    master_gps = pd.read_csv(master_gps_path)
    new_gps = pd.read_csv(new_gps_path)
    # get new codes
    new_codes = new_gps['CODE'].tolist()
    # get existing codes
    existing_codes = master_gps['CODE'].tolist()
    # get codes to add
    codes_to_add = [code for code in new_codes if code not in existing_codes]
    # get new locations
    new_locations = new_gps[new_gps['CODE'].isin(codes_to_add)]['LOCATION'].tolist()
    # get existing locations
    existing_locations = master_gps['LOCATION'].tolist()
    # get locations to add
    locations_to_add = [location for location in new_locations if location not in existing_locations]
    # get new gps data
    new_gps_data = new_gps[new_gps['CODE'].isin(codes_to_add)][['CODE', 'LOCATION', 'ADDRESS', 'LATITUDE', 'LONGITUDE', 'BRAND']]
    # get existing gps data
    existing_gps_data = master_gps[master_gps['CODE'].isin(existing_codes)][['CODE', 'LOCATION', 'ADDRESS', 'LATITUDE', 'LONGITUDE', 'BRAND']]
    # get gps data to add
    gps_data_to_add = new_gps_data[new_gps_data['CODE'].isin(codes_to_add)]
    # add new gps data
    master_gps = pd.concat([master_gps, gps_data_to_add], ignore_index=True)
    # drop duplicates
    master_gps = master_gps.drop_duplicates(subset=['CODE'], keep='first')
    master_gps.to_csv(master_gps_path, index=False)
    return master_gps

def update_master_matrix(master_matrix_path, new_matrix_path):
    pass