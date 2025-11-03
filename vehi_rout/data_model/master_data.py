import pandas as pd
import os
from vehi_rout.utils.helper_utils import get_osrm_data

class MasterData:
    def __init__(self, check_df):
        # Load master GPS and OSRM matrices
        self.master_gps = pd.read_csv('data/master/master_gps.csv', dtype={'CODE': str})
        self.distance_df = pd.read_csv('data/master/osrm_distance_matrix.csv', index_col=0, dtype={0: str})
        self.distance_df.index = self.distance_df.index.astype(str)
        self.distance_df.columns = self.distance_df.columns.astype(str)
        self.duration_df = pd.read_csv('data/master/osrm_duration_matrix.csv', index_col=0, dtype={0: str})
        self.duration_df.index = self.duration_df.index.astype(str)
        self.duration_df.columns = self.duration_df.columns.astype(str)
        self.check_df = check_df

    def update_master_with_gps_df(self, new_gps_df, osrm_getter=None):
        """Update master GPS and OSRM matrices based on an incoming GPS DataFrame.

        This treats the uploaded CSV as a delta: it updates coordinates and other columns
        (LOCATION, ADDRESS, BRAND, DISTRICT) for existing codes and adds new codes.
        It does NOT remove codes absent from the uploaded file. OSRM matrices are only
        updated for codes with changed GPS coordinates or new codes, using symmetry to
        avoid redundant calculations (dist[i,j] = dist[j,i], dur[i,j] = dur[j,i]).

        Args:
            new_gps_df (pd.DataFrame): DataFrame with columns ['CODE', 'LATITUDE', 'LONGITUDE']
                and optionally ['LOCATION', 'ADDRESS', 'BRAND', 'DISTRICT']
            osrm_getter (callable, optional): function(origin_tuple, dest_tuple) -> (path, distance_km, duration_min).
                If None, defaults to vehi_rout.utils.helper_utils.get_osrm_data.

        Returns:
            dict: {'changed_gps': [codes], 'changed_non_gps': [codes], 'added': [codes], 'master_path': path}
        """
        if osrm_getter is None:
            osrm_getter = get_osrm_data

        # Validate required columns
        required_cols = {'CODE', 'LATITUDE', 'LONGITUDE'}
        if not required_cols.issubset(new_gps_df.columns):
            raise ValueError(f"new_gps_df must contain columns: {sorted(list(required_cols))}")

        # Define optional columns to check
        optional_cols = {'LOCATION', 'ADDRESS', 'BRAND', 'DISTRICT'}
        available_optional_cols = [col for col in optional_cols if col in new_gps_df.columns and col in self.master_gps.columns]

        # Normalize and copy
        cur = self.master_gps.copy()
        cur['CODE'] = cur['CODE'].astype(str)
        new = new_gps_df.copy()
        new['CODE'] = new['CODE'].astype(str)

        # Validate latitude and longitude
        try:
            new['LATITUDE'] = new['LATITUDE'].astype(float)
            new['LONGITUDE'] = new['LONGITUDE'].astype(float)
            if not (new['LATITUDE'].between(-90, 90).all() and new['LONGITUDE'].between(-180, 180).all()):
                raise ValueError("LATITUDE must be between -90 and 90, LONGITUDE between -180 and 180")
        except Exception as e:
            raise ValueError(f"Invalid LATITUDE or LONGITUDE values: {str(e)}")

        # Check for duplicate codes
        if new['CODE'].duplicated().any():
            raise ValueError(f"Duplicate CODE values found in new_gps_df: {new[new['CODE'].duplicated()]['CODE'].tolist()}")

        # Build lookups
        cur_coords = cur.set_index('CODE')[['LATITUDE', 'LONGITUDE'] + available_optional_cols].to_dict('index')
        new_coords = new.set_index('CODE')[['LATITUDE', 'LONGITUDE'] + available_optional_cols].to_dict('index')

        changed_gps_codes = []
        changed_non_gps_codes = []
        added_codes = []

        # Detect changed and added codes
        for code in new_coords:
            if code in cur_coords:
                # Check GPS changes
                old_lat = float(cur_coords[code]['LATITUDE'])
                old_lon = float(cur_coords[code]['LONGITUDE'])
                new_lat = float(new_coords[code]['LATITUDE'])
                new_lon = float(new_coords[code]['LONGITUDE'])
                if abs(old_lat - new_lat) > 1e-6 or abs(old_lon - new_lon) > 1e-6:
                    changed_gps_codes.append(code)
                # Check non-GPS columns if no GPS change
                else:
                    for col in available_optional_cols:
                        old_val = cur_coords[code].get(col)
                        new_val = new_coords[code].get(col)
                        # Handle NaN and None comparisons
                        if pd.isna(old_val) and pd.isna(new_val):
                            continue
                        if old_val != new_val:
                            changed_non_gps_codes.append(code)
                            break
            else:
                added_codes.append(code)

        # Update OSRM matrices only for changed GPS or added codes
        if changed_gps_codes or added_codes:
            dist_df = self.distance_df.copy()
            dur_df = self.duration_df.copy()
            dist_df.index = dist_df.index.astype(str)
            dist_df.columns = dist_df.columns.astype(str)
            dur_df.index = dur_df.index.astype(str)
            dur_df.columns = dur_df.columns.astype(str)

            existing_codes = list(dist_df.index)
            if added_codes:
                new_index = existing_codes + added_codes
                dist_df = dist_df.reindex(index=new_index, columns=new_index, fill_value=float('inf'))
                dur_df = dur_df.reindex(index=new_index, columns=new_index, fill_value=float('inf'))
                existing_codes = new_index

            to_compute = changed_gps_codes + added_codes
            # Track processed pairs to avoid redundant calculations
            processed_pairs = set()
            
            for code in to_compute:
                coords = new_coords.get(code, cur_coords.get(code))
                if not coords:
                    continue
                origin = (float(coords['LATITUDE']), float(coords['LONGITUDE']))

                for other in existing_codes:
                    # Skip self and already processed pairs
                    if other == code:
                        dist_df.at[code, code] = 0.0
                        dur_df.at[code, code] = 0.0
                        continue
                    # Create a canonical pair representation (sorted to ensure (i,j) and (j,i) are treated as the same)
                    pair = tuple(sorted([code, other]))
                    if pair in processed_pairs:
                        continue
                    processed_pairs.add(pair)

                    other_coords = new_coords.get(other, cur_coords.get(other))
                    if not other_coords:
                        dist_df.at[code, other] = float('inf')
                        dur_df.at[code, other] = float('inf')
                        dist_df.at[other, code] = float('inf')
                        dur_df.at[other, code] = float('inf')
                        continue

                    dest = (float(other_coords['LATITUDE']), float(other_coords['LONGITUDE']))
                    try:
                        _, dist, dur = osrm_getter(origin, dest)
                    except Exception as e:
                        dist = dur = float('inf')

                    # Assign symmetric values
                    dist_df.at[code, other] = dist
                    dur_df.at[code, other] = dur
                    dist_df.at[other, code] = dist
                    dur_df.at[other, code] = dur

            # Persist updated matrices
            try:
                dist_df.to_csv('data/master/osrm_distance_matrix.csv')
                dur_df.to_csv('data/master/osrm_duration_matrix.csv')
            except Exception as e:
                raise IOError(f"Failed to write OSRM matrices: {str(e)}")
        else:
            dist_df = self.distance_df
            dur_df = self.duration_df

        # Update master_gps for changed (GPS or non-GPS) and added codes
        master_updated = cur.copy()
        all_cols = ['CODE', 'LATITUDE', 'LONGITUDE'] + available_optional_cols
        master_updated = master_updated[~master_updated['CODE'].isin(changed_gps_codes + changed_non_gps_codes)]
        to_update = new[new['CODE'].isin(changed_gps_codes + changed_non_gps_codes + added_codes)][all_cols]
        master_updated = pd.concat([master_updated, to_update], ignore_index=True)

        # Ensure no duplicates
        if master_updated['CODE'].duplicated().any():
            raise ValueError(f"Duplicate CODE values in updated master_gps: {master_updated[master_updated['CODE'].duplicated()]['CODE'].tolist()}")

        # Persist updated master_gps
        try:
            master_updated.to_csv('data/master/master_gps.csv', index=False)
        except Exception as e:
            raise IOError(f"Failed to write master_gps.csv: {str(e)}")

        # Update in-memory objects
        self.master_gps = master_updated
        self.distance_df = dist_df
        self.duration_df = dur_df

        return {
            'changed_gps': changed_gps_codes,
            'changed_non_gps': changed_non_gps_codes,
            'added': added_codes,
            'master_path': 'data/master/master_gps.csv'
        }