"""
Visualization module for the Vehicle Routing Problem.
Provides functions to visualize routes on a map.
"""

import pandas as pd
import csv
import os
import random
import ast
from collections import defaultdict
from functools import reduce
from vehi_rout.utils.helper_utils import get_osrm_data
import folium
import folium.plugins

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
            # Reconstruct the path from the string (using ast.literal_eval for safety)
            path_str = row['path_coordinates']
            try:
                path_coords = ast.literal_eval(path_str)
                route_cache[tuple(sorted([origin_code, dest_code]))] = path_coords
            except (ValueError, SyntaxError) as e:
                print(f"Warning: Could not parse path coordinates for {origin_code} to {dest_code}: {e}")
        print(f"Loaded {len(route_cache)} cached routes from {cache_file}")
    except Exception as e:
        print(f"Warning: Failed to load cache file {cache_file}: {e}")
else:
    print(f"No cache file found at {cache_file}, starting fresh")


def generate_random_color():
    """Generate a random color in hexadecimal format."""
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return f'#{r:02x}{g:02x}{b:02x}'

def visualize_routes_per_vehicle(master_df, route_dict, day, use_distance=False):
    """
    Visualize the route for each vehicle on a separate map using folium, with cached route paths.
    :param master_df: DataFrame containing master GPS data (CODE, LATITUDE, LONGITUDE, etc.)
    :param route_dict: Dictionary containing route details for each vehicle
    :param day: Day number for the map title
    :param use_distance: Boolean indicating whether to use distance or time for route metrics
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

            # 🔥 Check if path has enough points
            if path_cords and len(path_cords) > 2:
                path_coordinates.extend(path_cords)
                print(f"Added path from {origin_code} to {dest_code} with {len(path_cords)} points")
            else:
                print(f"Skipping path from {origin_code} to {dest_code} — insufficient points ({len(path_cords)} points)")

        # Create a new map centered at the first location of the route
        if route_nodes and route_nodes[0] in code_to_coords:
            start_coords = [code_to_coords[route_nodes[0]][0], code_to_coords[route_nodes[0]][1]]
            m = folium.Map(location=start_coords, zoom_start=10)
        else:
            m = folium.Map(location=[master_df['LATITUDE'].mean(), master_df['LONGITUDE'].mean()], zoom_start=10)
            print(f"Warning: No valid start coordinates for vehicle {vehicle_id}, using map center")

        # Add markers for each node in the route with sequence numbers
        for i, node in enumerate(route_nodes):
            if node in code_to_coords:
                coords = [code_to_coords[node][0], code_to_coords[node][1]]
                # Special marker for depot (first and last node)
                if node == '0' or (i == 0 or i == len(route_nodes) - 1):
                    # Create a custom icon for the depot with '0' as the label
                    depot_icon = folium.DivIcon(
                        icon_size=(50, 50),
                        icon_anchor=(25, 25),
                        html=f'<div style="font-size: 16pt; font-weight: bold; color: white; background-color: red; border-radius: 50%; width: 50px; height: 50px; text-align: center; line-height: 50px;">0</div>',
                    )

                    folium.Marker(
                        location=coords,
                        popup=f"DEPOT (SMAK_KADAWATHA)",
                        icon=depot_icon
                    ).add_to(m)
                else:
                    # Create a custom icon with the sequence number
                    icon = folium.DivIcon(
                        icon_size=(30, 30),
                        icon_anchor=(15, 15),
                        html=f'<div style="font-size: 12pt; color: white; background-color: blue; border-radius: 50%; width: 30px; height: 30px; text-align: center; line-height: 30px;">{i}</div>',
                    )

                    folium.Marker(
                        location=coords,
                        popup=f"Stop {i}: {node} - {master_df[master_df['CODE'] == node]['LOCATION'].values[0] if not master_df[master_df['CODE'] == node].empty else 'Unknown'}",
                        icon=icon
                    ).add_to(m)

        # Add the route path if coordinates are available
        if path_coordinates:
            # Generate a unique color for this vehicle's route
            route_color = generate_random_color()

            # Add route path with arrows to show direction
            folium.PolyLine(
                locations=path_coordinates,
                color=route_color,
                weight=5,     # Increased weight for better visibility
                opacity=0.9,
                popup=f"Vehicle {vehicle_id} Route",
                tooltip=f"Vehicle {vehicle_id}: {route_info.get('num_visits', 0)} stops, {route_info.get('route_distance' if use_distance else 'route_time', 0)} {'km' if use_distance else 'mins'}"
            ).add_to(m)

            # Add arrows to indicate direction
            folium.plugins.AntPath(
                locations=path_coordinates,
                color=route_color,
                weight=5,
                opacity=0.8,
                delay=1000,  # Animation delay
                dash_array=[10, 20],  # Pattern of the dash
                pulse_color='#FFFFFF'
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


def save_route_details_to_csv(route_dict, day, use_distance=False, file_path=None):
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
                     f'Max {metric_name.capitalize()} ({unit})', 'Within Limit', 'Route']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        for vehicle_id, route_info in route_dict.items():
            route_metric = route_info.get(f"route_{metric_name}", 0)
            num_visits = route_info.get("num_visits", 0)
            max_metric = route_info.get(f"max_{metric_name}_limit", 0)
            within_limit = route_info.get("within_limit", False)
            route_nodes = ' -> '.join(map(str, route_info.get("route_nodes", [])))

            writer.writerow({
                'Day': day + 1,
                'Vehicle': vehicle_id,
                'Stops': num_visits,
                f'{metric_name.capitalize()} ({unit})': route_metric,
                f'Max {metric_name.capitalize()} ({unit})': max_metric,
                'Within Limit': 'Yes' if within_limit else 'No',
                'Route': route_nodes
            })

    print(f"Route details saved to {file_path}")
    return file_path