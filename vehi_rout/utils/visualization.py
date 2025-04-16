import pandas as pd
import csv
from collections import defaultdict
import os
from functools import reduce
from vehi_rout.utils.helper_utils import get_osrm_data
import folium

# Global cache to store route paths (key: tuple of (origin_code, dest_code), value: path_coordinates)
route_cache = defaultdict(list)

# Cache file path for CSV
cache_file = '../data/csv/route_cache.csv'

# Load existing cache from CSV file at the start
if os.path.exists(cache_file):
    try:
        df = pd.read_csv(cache_file)
        for _, row in df.iterrows():
            origin_code, dest_code = row['origin_code'], row['dest_code']
            # Reconstruct the path from the string (assuming it's stored as a JSON string)
            path_str = row['path_coordinates']
            path_coords = eval(path_str)  # Use eval carefully; better to use ast.literal_eval for safety
            route_cache[tuple(sorted([origin_code, dest_code]))] = path_coords
        print(f"Loaded {len(route_cache)} cached routes from {cache_file}")
    except Exception as e:
        print(f"Warning: Failed to load cache file {cache_file}: {e}")
else:
    print(f"No cache file found at {cache_file}, starting fresh")

def visualize_routes_per_vehicle(master_df, route_dict, day):
    """
    Visualize the route for each vehicle on a separate map using folium, with cached route paths.
    :param master_df: DataFrame containing master GPS data (CODE, LATITUDE, LONGITUDE, etc.)
    :param route_dict: Dictionary containing route details for each vehicle
    :param day: Day number for the map title
    :return: Dictionary of folium.Map objects keyed by vehicle_id
    """
    if not isinstance(route_dict, dict) or not route_dict:
        print("Error: route_dict is not a valid dictionary or is empty")
        return {}

    maps_dict = {}  # Dictionary to store individual maps for each vehicle

    # Create a mapping from CODE to coordinates for quick lookup
    try:
        code_to_coords = dict(zip(master_df['CODE'], master_df[['LATITUDE', 'LONGITUDE']].values))
    except Exception as e:
        print(f"Error creating code_to_coords mapping: {e}")
        return {}

    for vehicle_id, route_info in route_dict.items():
        route_nodes = route_info.get('route_nodes', [])
        path_coordinates = []

        print(f"Processing route for vehicle {vehicle_id}: {route_nodes}")  # Debug: Print route nodes

        # Get the path between consecutive nodes using cached data or OSRM
        for i in range(len(route_nodes) - 1):
            origin_code = route_nodes[i]
            dest_code = route_nodes[i + 1]
            
            # Check if path is in cache
            cache_key = tuple(sorted([origin_code, dest_code]))  # Use sorted tuple for bidirectional caching
            if cache_key in route_cache and route_cache[cache_key]:
                path_cords = route_cache[cache_key]
                print(f"Using cached path for {origin_code} to {dest_code}")
            else:
                # Find coordinates for origin and destination
                if origin_code not in code_to_coords or dest_code not in code_to_coords:
                    print(f"Warning: Node {origin_code} or {dest_code} not found in master_df for vehicle {vehicle_id}")
                    continue
                
                origin = (code_to_coords[origin_code][0], code_to_coords[origin_code][1])
                destination = (code_to_coords[dest_code][0], code_to_coords[dest_code][1])
                
                print(f"Fetching path from {origin_code} ({origin}) to {dest_code} ({destination})")
                path_cords, _, _ = get_osrm_data(origin, destination)
                if path_cords:
                    route_cache[cache_key] = path_cords  # Store the path in cache
                    print(f"Path cached for {origin_code} to {dest_code}: {path_cords[:5]}... (total {len(path_cords)} points)")
                else:
                    print(f"Warning: No path found between {origin_code} and {dest_code} for vehicle {vehicle_id}")
                    continue
            
            path_coordinates.extend(path_cords)

        # Create a new map centered at the first location of the route
        if route_nodes and route_nodes[0] in code_to_coords:
            start_coords = [code_to_coords[route_nodes[0]][0], code_to_coords[route_nodes[0]][1]]
            m = folium.Map(location=start_coords, zoom_start=10)
        else:
            m = folium.Map(location=[master_df['LATITUDE'].mean(), master_df['LONGITUDE'].mean()], zoom_start=10)
            print(f"Warning: No valid start coordinates for vehicle {vehicle_id}, using map center")

        # Add markers for each node in the route
        for node in route_nodes:
            if node in code_to_coords:
                coords = [code_to_coords[node][0], code_to_coords[node][1]]
                folium.Marker(
                    location=coords,
                    popup=f"{node}: {master_df[master_df['CODE'] == node]['LOCATION'].values[0] if not master_df[master_df['CODE'] == node].empty else 'Unknown'}",
                    icon=folium.Icon(color='blue', icon='info-sign')
                ).add_to(m)

        # Add the route path if coordinates are available
        if path_coordinates:
            folium.PolyLine(
                locations=path_coordinates,
                color='red',  # Highlighted red color for the path
                weight=5,     # Increased weight for better visibility
                opacity=0.9,
                popup=f"Vehicle {vehicle_id} Route (Time: {route_info.get('route_time', 0)} mins)"
            ).add_to(m)
            print(f"Plotted path for vehicle {vehicle_id} with {len(path_coordinates)} coordinates")
        else:
            print(f"No path coordinates available for vehicle {vehicle_id}. Route not plotted.")

        # Add title
        title_html = f'<h3 align="center" style="font-size:16px">Day {day + 1} - Vehicle {vehicle_id} Route</h3>'
        m.get_root().html.add_child(folium.Element(title_html))

        # Save the map and store in dictionary
        map_filename = f"day_{day + 1}_vehicle_{vehicle_id}_route.html"
        maps_dict[vehicle_id] = m

    # Save the updated cache to CSV
    try:
        # Convert cache to list of rows for CSV
        cache_rows = []
        for key, value in route_cache.items():
            origin_code, dest_code = key
            # Convert path coordinates to a string (e.g., JSON string for simplicity)
            path_str = str(value)  # Simple string representation; for safety, use json.dumps(value)
            cache_rows.append({'origin_code': origin_code, 'dest_code': dest_code, 'path_coordinates': path_str})

        # Save to CSV
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['origin_code', 'dest_code', 'path_coordinates'])
            writer.writeheader()
            writer.writerows(cache_rows)
        print(f"Saved {len(route_cache)} cached routes to {cache_file}")
    except Exception as e:
        print(f"Warning: Failed to save cache file {cache_file}: {e}")

    return maps_dict