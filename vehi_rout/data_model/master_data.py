import pandas as pd
from vehi_rout.utils.helper_utils import get_osrm_data


class MasterData:
    def __init__(self, check_df):
        # Load master GPS and OSRM matrices
        self.master_gps = pd.read_csv('data/master/master_gps.csv')
        self.distance_df = pd.read_csv('data/master/osrm_distance_matrix.csv', index_col=0)
        self.distance_df.index = self.distance_df.index.astype(str)
        self.distance_df.columns = self.distance_df.columns.astype(str)
        self.duration_df = pd.read_csv('data/master/osrm_duration_matrix.csv', index_col=0)
        self.duration_df.index = self.duration_df.index.astype(str)
        self.duration_df.columns = self.duration_df.columns.astype(str)
        self.check_df = check_df

    def update_master_with_gps_df(self, new_gps_df, osrm_getter=None):
        """Update master GPS and osrm matrices based on an incoming GPS DataFrame.

        This treats the uploaded CSV as a delta: it will update coordinates for
        existing codes (if changed) and add brand-new codes. It will NOT remove
        codes that are absent from the uploaded file.

        Args:
            new_gps_df (pd.DataFrame): DataFrame with columns at least ['CODE','LATITUDE','LONGITUDE']
            osrm_getter (callable, optional): function(origin_tuple, dest_tuple) -> (path, distance_km, duration_min).
                If None, defaults to vehi_rout.utils.helper_utils.get_osrm_data.

        Returns:
            dict: {'changed': [codes], 'added': [codes], 'master_path': path}
        """
        if osrm_getter is None:
            osrm_getter = get_osrm_data

        # Normalize and copy
        cur = self.master_gps.copy()
        cur['CODE'] = cur['CODE'].astype(str)
        new = new_gps_df.copy()
        new['CODE'] = new['CODE'].astype(str)

        # Build coordinate lookups
        cur_coords = cur.set_index('CODE')[['LATITUDE', 'LONGITUDE']].to_dict('index')
        new_coords = new.set_index('CODE')[['LATITUDE', 'LONGITUDE']].to_dict('index')

        changed_codes = []
        added_codes = []

        # Detect changed codes (present in both but lat/lon changed)
        for code, coords in cur_coords.items():
            if code in new_coords:
                try:
                    old_lat = float(coords['LATITUDE'])
                    old_lon = float(coords['LONGITUDE'])
                    new_lat = float(new_coords[code]['LATITUDE'])
                    new_lon = float(new_coords[code]['LONGITUDE'])
                except Exception:
                    continue
                if abs(old_lat - new_lat) > 1e-6 or abs(old_lon - new_lon) > 1e-6:
                    changed_codes.append(code)

        # Detect added codes (present in upload but not in current master)
        for code in new_coords.keys():
            if code not in cur_coords:
                added_codes.append(code)

        # Start with copies of the current matrices
        dist_df = self.distance_df.copy()
        dur_df = self.duration_df.copy()

        # Ensure indices/columns are strings
        dist_df.index = dist_df.index.astype(str)
        dist_df.columns = dist_df.columns.astype(str)
        dur_df.index = dur_df.index.astype(str)
        dur_df.columns = dur_df.columns.astype(str)

        # We'll update distances for changed_codes and add rows/cols for added_codes.
        existing_codes = list(dist_df.index.astype(str))

        # If there are new codes, expand the matrices to include them (filled with NaN)
        if added_codes:
            new_index = existing_codes + added_codes
            dist_df = dist_df.reindex(index=new_index, columns=new_index)
            dur_df = dur_df.reindex(index=new_index, columns=new_index)
            existing_codes = new_index

        # Combined list of codes we need to (re)compute distances for
        to_compute = list(dict.fromkeys(changed_codes + added_codes))

        # For each code that changed or was added, compute distances/durations
        for code in to_compute:
            coords = new_coords.get(code) or cur_coords.get(code)
            if not coords:
                continue
            origin = (float(coords['LATITUDE']), float(coords['LONGITUDE']))

            # distance/duration to and from every other existing code
            for other in existing_codes:
                if other == code:
                    # distance to self = 0
                    dist_df.at[code, code] = 0.0
                    dur_df.at[code, code] = 0.0
                    continue

                # get coordinates for the other code (prefer new if available)
                other_coords = new_coords.get(other) or cur_coords.get(other)
                if not other_coords:
                    # leave as inf/NaN if coords unavailable
                    dist_df.at[code, other] = float('inf')
                    dur_df.at[code, other] = float('inf')
                    dist_df.at[other, code] = float('inf')
                    dur_df.at[other, code] = float('inf')
                    continue

                dest = (float(other_coords['LATITUDE']), float(other_coords['LONGITUDE']))
                # Compute origin -> dest
                try:
                    _, dist_to_other, dur_to_other = osrm_getter(origin, dest)
                except Exception:
                    dist_to_other, dur_to_other = float('inf'), float('inf')

                # Compute other -> origin
                try:
                    _, dist_from_other, dur_from_other = osrm_getter(dest, origin)
                except Exception:
                    dist_from_other, dur_from_other = float('inf'), float('inf')

                # Assign into dataframes
                dist_df.at[code, other] = dist_to_other
                dur_df.at[code, other] = dur_to_other
                dist_df.at[other, code] = dist_from_other
                dur_df.at[other, code] = dur_from_other

        # Update master_gps: update coords for changed codes, append added codes.
        master_updated = cur.copy()
        if changed_codes:
            for code in changed_codes:
                row_idx = master_updated[master_updated['CODE'] == code].index
                if len(row_idx) > 0:
                    i = row_idx[0]
                    master_updated.at[i, 'LATITUDE'] = float(new_coords[code]['LATITUDE'])
                    master_updated.at[i, 'LONGITUDE'] = float(new_coords[code]['LONGITUDE'])

        if added_codes:
            to_add = new[new['CODE'].isin(added_codes)].copy()
            # append new rows
            master_updated = pd.concat([master_updated, to_add], ignore_index=True)

        # Persist updated files
        master_updated.to_csv('data/master/master_gps.csv', index=False)
        dist_df.to_csv('data/master/osrm_distance_matrix.csv')
        dur_df.to_csv('data/master/osrm_duration_matrix.csv')

        # Update in-memory objects
        self.master_gps = master_updated
        self.distance_df = dist_df
        self.duration_df = dur_df

        return {
            'changed': changed_codes,
            'added': added_codes,
            'master_path': 'data/master/master_gps.csv'
        }