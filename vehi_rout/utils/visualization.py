"""
Visualization module for the Vehicle Routing Problem.
Provides functions to visualize routes on a map with OSRM-based paths and caching.
"""

import os
import csv
import ast
import random
import pandas as pd
import folium
import folium.plugins
from collections import defaultdict
from vehi_rout.utils.helper_utils import get_osrm_data

# Cache path and global variable
CACHE_FILE = '../data/csv/route_cache.csv'
route_cache = defaultdict(list)


def generate_random_color():
    return f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"


def load_route_cache():
    """Load cached routes from CSV file into memory."""
    global route_cache
    route_cache.clear()
    if not os.path.exists(CACHE_FILE):
        print(f"No cache file found at {CACHE_FILE}, starting fresh")
        return
    try:
        df = pd.read_csv(CACHE_FILE)
        for _, row in df.iterrows():
            key = tuple(sorted([row['origin_code'], row['dest_code']]))
            try:
                coords = ast.literal_eval(row['path_coordinates'])
                if coords and len(coords) > 2:
                    route_cache[key] = coords
            except Exception as e:
                print(f"Failed to parse path for {key}: {e}")
        print(f"Loaded {len(route_cache)} cached routes from {CACHE_FILE}")
    except Exception as e:
        print(f"Error reading cache file {CACHE_FILE}: {e}")


def save_route_cache():
    """Save route cache to CSV."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['origin_code', 'dest_code', 'path_coordinates'])
            writer.writeheader()
            for (origin, dest), path in route_cache.items():
                writer.writerow({
                    'origin_code': origin,
                    'dest_code': dest,
                    'path_coordinates': str(path)
                })
        print(f"Saved {len(route_cache)} cached routes to {CACHE_FILE}")
    except Exception as e:
        print(f"Error saving cache: {e}")


def visualize_routes_per_vehicle(master_df, route_dict, day, use_distance=False):
    if not route_dict:
        print("No routes to visualize.")
        return {}

    maps_dict = {}
    code_to_coords = dict(zip(master_df['CODE'], master_df[['LATITUDE', 'LONGITUDE']].values))

    for vehicle_id, route_info in route_dict.items():
        route_nodes = route_info.get('route_nodes', [])
        path_coordinates = []

        for i in range(len(route_nodes) - 1):
            origin, dest = route_nodes[i], route_nodes[i + 1]
            key = tuple(sorted([origin, dest]))

            if key in route_cache and len(route_cache[key]) > 2:
                segment = route_cache[key]
            else:
                if origin not in code_to_coords or dest not in code_to_coords:
                    print(f"Missing GPS data for {origin} or {dest}, skipping.")
                    continue
                orig_coords = tuple(code_to_coords[origin])
                dest_coords = tuple(code_to_coords[dest])
                segment, _, _ = get_osrm_data(orig_coords, dest_coords)
                if segment and len(segment) > 2:
                    route_cache[key] = segment
                else:
                    print(f"No valid path found between {origin} and {dest}, skipping.")
                    continue

            path_coordinates.extend(segment)

        # Create map
        start_coords = code_to_coords.get(route_nodes[0], [master_df['LATITUDE'].mean(), master_df['LONGITUDE'].mean()])
        m = folium.Map(location=start_coords, zoom_start=10)

        # Add path
        if path_coordinates:
            color = generate_random_color()
            folium.PolyLine(locations=path_coordinates, color=color, weight=5, opacity=0.9).add_to(m)
            folium.plugins.AntPath(locations=path_coordinates, color=color).add_to(m)

        # Add markers
        for i, node in enumerate(route_nodes):
            if node not in code_to_coords:
                continue
            lat, lon = code_to_coords[node]
            if i == 0 or i == len(route_nodes) - 1:
                icon = folium.DivIcon(html=f'<div style="background-color:red;color:white;border-radius:50%;width:30px;height:30px;text-align:center;line-height:30px;font-weight:bold">0</div>')
                popup = "DEPOT"
            else:
                icon = folium.DivIcon(html=f'<div style="background-color:blue;color:white;border-radius:50%;width:25px;height:25px;text-align:center;line-height:25px">{i}</div>')
                loc_name = master_df.loc[master_df['CODE'] == node, 'LOCATION'].values
                popup = f"Stop {i}: {node} - {loc_name[0] if len(loc_name) else 'Unknown'}"
            folium.Marker(location=[lat, lon], popup=popup, icon=icon).add_to(m)

        maps_dict[vehicle_id] = m

        # Title
        title_html = f'<h3 align="center">Day {day + 1} - Vehicle {vehicle_id} Route</h3>'
        m.get_root().html.add_child(folium.Element(title_html))

    save_route_cache()
    return maps_dict



def print_route_summary(route_dict, use_distance=False, file_path=None):
    """
    Print a summary of the routes and optionally save to a file.

    Args:
        route_dict: Dictionary containing route information for each vehicle
        use_distance: Boolean indicating whether to use distance or time
        file_path: Path to save the summary to (optional)

    Returns:
        tuple: (total_metric, total_visits)
    """
    metric_name = "distance" if use_distance else "time"
    unit = "km" if use_distance else "mins"

    total_metric = 0
    total_visits = 0

    # Create summary lines
    summary_lines = []
    summary_lines.append(f"Route Summary:")
    summary_lines.append(f"{'':<3} {'Vehicle':<10} {'Stops':<10} {metric_name.capitalize():<15} {'Within Limit':<15}")
    summary_lines.append("-" * 55)

    for vehicle_id, route_info in route_dict.items():
        route_metric = route_info.get(f"route_{metric_name}", 0)
        num_visits = route_info.get("num_visits", 0)
        max_metric = route_info.get(f"max_{metric_name}_limit", 0)
        within_limit = route_info.get("within_limit", False)

        summary_lines.append(f"{'':<3} {vehicle_id:<10} {num_visits:<10} {route_metric:<10} {unit:<4} {'Yes' if within_limit else 'No':<15}")

        total_metric += route_metric
        total_visits += num_visits

    summary_lines.append("-" * 55)
    summary_lines.append(f"{'':<3} {'Total':<10} {total_visits:<10} {total_metric:<10} {unit:<4}")

    # Print summary
    for line in summary_lines:
        print(line)

    # Save to file if path is provided
    if file_path:
        with open(file_path, 'w') as f:
            for line in summary_lines:
                f.write(line + '\n')
            print(f"Summary saved to {file_path}")

    return total_metric, total_visits


def save_route_details_to_csv(demand_df, route_dict, day, use_distance=False, file_path=None):
    """
    Save detailed route information to a CSV file.

    Args:
        route_dict: Dictionary containing route information for each vehicle
        day: Day index (0-based)
        use_distance: Boolean indicating whether to use distance or time
        file_path: Path to save the CSV file (optional)

    Returns:
        str: Path to the saved file or None if not saved
    """
    import csv
    import os

    if file_path is None:
        os.makedirs("output/csv", exist_ok=True)
        file_path = f"output/csv/day_{day+1}_routes.csv"

    metric_name = "distance" if use_distance else "time"
    unit = "km" if use_distance else "mins"

    with open(file_path, 'w', newline='') as csvfile:
        fieldnames = ['Day', 'Vehicle', 'Stops', f'{metric_name.capitalize()} ({unit})',
                     f'Max {metric_name.capitalize()} ({unit})', 'Within Limit','PO Value','VOLUME Value', 'Route']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        for vehicle_id, route_info in route_dict.items():
            route_metric = route_info.get(f"route_{metric_name}", 0)
            num_visits = route_info.get("num_visits", 0)
            max_metric = route_info.get(f"max_{metric_name}_limit", 0)
            within_limit = route_info.get("within_limit", False)
            route_nodes = route_info.get("route_nodes", [])
            po_value_df = demand_df[demand_df['CODE'].isin(route_nodes)]
            # Calculate PO Value
            po_value = 0.0
            if not po_value_df.empty and 'SALE' in po_value_df.columns:
                if po_value_df['SALE'].dtype == object:  # Check if SALE is string type
                    po_value = pd.to_numeric(po_value_df['SALE'].str.replace(',', '', regex=False), errors='coerce').fillna(0).sum()
                else:  # Assume numeric (int or float)
                    po_value = po_value_df['SALE'].sum()

            # Calculate VOLUME Value
            vol_value = 0.0
            if not po_value_df.empty and 'VOLUME' in po_value_df.columns:
                if po_value_df['VOLUME'].dtype == object:  # Check if VOLUME is string type
                    vol_value = pd.to_numeric(po_value_df['VOLUME'].str.replace(',', '', regex=False), errors='coerce').fillna(0).sum()
                else:  # Assume numeric (int or float)
                    vol_value = po_value_df['VOLUME'].sum()
            route_str = ' -> '.join(
                        f"{code} ({demand_df.loc[demand_df['CODE'] == code, 'LOCATION'].values[0]})"
                        if code in demand_df['CODE'].values else str(code)
                        for code in route_nodes
                    )

            writer.writerow({
                'Day': day + 1,
                'Vehicle': vehicle_id,
                'Stops': num_visits,
                f'{metric_name.capitalize()} ({unit})': route_metric,
                f'Max {metric_name.capitalize()} ({unit})': max_metric,
                'Within Limit': 'Yes' if within_limit else 'No',
                'PO Value':po_value,
                'VOLUME Value':vol_value,
                'Route': route_str
            })

    print(f"Route details saved to {file_path}")
    return file_path