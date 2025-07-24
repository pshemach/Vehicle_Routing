"""
Controller module for the Vehicle Routing Problem.
Orchestrates the entire process of solving the VRP.
"""

import pandas as pd
from datetime import datetime
import os

from vehi_rout.config import (
    DISTANCE_BASE_PENALTY,
    TIME_BASE_PENALTY,
    TOTAL_DAYS
)
from vehi_rout.utils.data_utils import (
    load_matrix_df,
    load_df,
    get_demand_df,
    update_demand_dic
)
from vehi_rout.utils.helper_utils import (
    get_penalty_list
)
from vehi_rout.utils.route_utils import sort_nodes_by_distance
from vehi_rout.utils.visualization import (
    visualize_routes_per_vehicle,
    print_route_summary,
    save_route_details_to_csv
)
from vehi_rout.solver.vrp_solver import (
    solve_vrp_for_day
)
from vehi_rout.solver.tsp_solver import (
    solve_tsp_for_route
)
from vehi_rout.routes.predefined_routes import PredefinedRouteManager

class VRPController:
    """Controller class for the Vehicle Routing Problem."""

    def __init__(self, use_distance=True):
        """
        Initialize the VRP controller.

        Args:
            use_distance: Boolean indicating whether to use distance or time
        """
        self.use_distance = use_distance
        self.base_penalty = DISTANCE_BASE_PENALTY if use_distance else TIME_BASE_PENALTY
        self.demand_df = None
        self.master_mat_df = None
        self.master_gps_df = None
        self.demand_dict = None
        self.penalty_list = None

        # Initialize vehicle configuration with default values
        import vehi_rout.config as config
        self.max_visits = config.MAX_VISITS_PER_VEHICLE
        self.max_distance = config.MAX_DISTANCE_PER_VEHICLE

        # Initialize route manager and vehicle routes
        self.route_manager = PredefinedRouteManager()
        self.vehicle_routes = {}  # Dictionary mapping vehicle_id to route_id

    def load_data(self, demand_path, matrix_path, gps_path):
        """
        Load data from files.

        Args:
            demand_path: Path to the demand file
            matrix_path: Path to the distance/time matrix file
            gps_path: Path to the GPS coordinates file
        """
        # Load demand data
        self.demand_df = get_demand_df(today_path=demand_path)

        # Convert CODE to string if it's numeric
        if self.demand_df['CODE'].dtype in ['float', 'int', 'int64']:
            self.demand_df['CODE'] = self.demand_df['CODE'].astype(int)
            self.demand_df['CODE'] = self.demand_df['CODE'].astype(str)
            print('Converting CODE to string')

        # Load distance/time matrix
        self.master_mat_df = load_matrix_df(path=matrix_path)

        # Load GPS coordinates
        self.master_gps_df = load_df(path=gps_path)

        # Add depot (SMAK_KADAWATHA) to the GPS data
        SMAK_KADAWATHA = (7.0038321, 79.9394804)
        smak_data = {
            "CODE": '0',
            "LOCATION": "SMAK",
            "ADDRESS": "Smak, Kadawatha, Western Province, Sri Lanka",
            "LATITUDE": SMAK_KADAWATHA[0],
            "LONGITUDE": SMAK_KADAWATHA[1]
        }

        # Always ensure the depot is in the master_gps_df
        import pandas as pd

        # Remove any existing depot entries
        if '0' in self.master_gps_df['CODE'].values:
            self.master_gps_df = self.master_gps_df[self.master_gps_df['CODE'] != '0']

        # Add depot to the GPS data at the beginning
        self.master_gps_df = pd.concat(
            [
                pd.DataFrame([smak_data]),
                self.master_gps_df
            ],
            ignore_index=True
        )
        print("Added depot (SMAK_KADAWATHA) to GPS data")

        # Create demand dictionary
        self.demand_dict = update_demand_dic(self.demand_df)

        # Calculate penalties
        today = datetime.now().strftime('%Y-%m-%d')
        self.penalty_list = get_penalty_list(self.demand_dict, self.base_penalty, TOTAL_DAYS, today)

        print(f"Loaded {len(self.demand_df)} demand records")
        print(f"Loaded {len(self.master_mat_df)} locations in distance/time matrix")
        print(f"Loaded {len(self.master_gps_df)} locations with GPS coordinates")


    def solve_single_day(self, day=0, max_nodes=None, save_visualization=False, output_folder=None):
        """
        Solve the VRP for a single day.

        Args:
            day: Day index (0-based)
            max_nodes: Maximum number of nodes to visit
            save_visualization: Boolean indicating whether to save visualization
            output_folder: Path to the output folder for saving results (if None, uses default)

        Returns:
            visited_nodes: Set of visited node indices
            route_dict: Dictionary containing route information for each vehicle
        """
        if self.demand_df is None or self.master_mat_df is None or self.master_gps_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")

        # Get nodes to visit
        all_nodes = list(range(1, len(self.master_mat_df)))

        # Sort nodes by distance from depot
        sorted_nodes = sort_nodes_by_distance(self.master_mat_df.values)

        # Limit the number of nodes if specified
        if max_nodes is not None and max_nodes < len(sorted_nodes):
            nodes_to_visit = sorted(sorted_nodes[:max_nodes])
        else:
            nodes_to_visit = all_nodes

        # Check if any vehicles have pre-defined routes
        has_predefined_routes = bool(self.vehicle_routes)

        if has_predefined_routes:
            # Initialize route dictionary and visited nodes
            route_dict = {}
            visited_nodes = set()

            # Process vehicles with pre-defined routes first
            for vehicle_id, route_id in self.vehicle_routes.items():
                # Ensure vehicle_id is an integer
                try:
                    vehicle_id_int = int(vehicle_id)
                    if vehicle_id_int >= len(self.max_visits):
                        print(f"Warning: Vehicle ID {vehicle_id} is out of range. Skipping.")
                        continue  # Skip if vehicle_id is out of range
                except (ValueError, TypeError):
                    print(f"Warning: Invalid vehicle ID {vehicle_id}. Skipping.")
                    continue

                route_data = self.route_manager.get_route(route_id)
                if not route_data:
                    continue  # Skip if route not found

                # Get shop codes from the pre-defined route
                shop_codes = route_data.get('shop_codes', [])

                # Filter shop codes to only include those in the current demand
                if self.demand_dict and 'key' in self.demand_dict:
                    demand_codes = set(self.demand_dict['key'])
                    filtered_shop_codes = [code for code in shop_codes if code in demand_codes]

                    # Log the filtering results
                    print(f"Pre-defined route '{route_id}': {len(shop_codes)} shops in route, {len(filtered_shop_codes)} shops in current demand")

                    # Use filtered shop codes
                    shop_codes = filtered_shop_codes

                    # Skip if no shops in this route are in the current demand
                    if not shop_codes:
                        print(f"Skipping route '{route_id}' as none of its shops are in the current demand")
                        continue

                # Solve TSP for this vehicle's pre-defined route
                try:
                    # Convert vehicle_id to integer for indexing
                    vehicle_id_int = int(vehicle_id)
                    route_nodes, route_info = solve_tsp_for_route(
                        self.master_mat_df,
                        shop_codes,
                        self.demand_dict,
                        self.use_distance,
                        self.max_distance[vehicle_id_int],
                        self.max_visits[vehicle_id_int]
                    )
                except (ValueError, TypeError, IndexError) as e:
                    print(f"Error solving TSP for vehicle {vehicle_id}: {str(e)}")
                    continue

                # Add to route dictionary and visited nodes
                if route_nodes:
                    route_dict[vehicle_id] = route_info
                    visited_nodes.update(set(route_nodes))

            # Get remaining nodes to visit (not in pre-defined routes)
            remaining_nodes = [node for node in nodes_to_visit if node not in visited_nodes]

            # Get vehicles without pre-defined routes
            # Convert vehicle_id keys to integers
            used_vehicles = set()
            for vehicle_id in self.vehicle_routes.keys():
                try:
                    used_vehicles.add(int(vehicle_id))
                except (ValueError, TypeError):
                    print(f"Warning: Invalid vehicle ID {vehicle_id} in vehicle_routes keys.")

            available_vehicles = [i for i in range(len(self.max_visits)) if i not in used_vehicles]

            if remaining_nodes and available_vehicles:
                # Create new max_visits and max_distance lists for remaining vehicles
                remaining_max_visits = [self.max_visits[i] for i in available_vehicles]
                remaining_max_distance = [self.max_distance[i] for i in available_vehicles]

                # Solve VRP for remaining nodes with remaining vehicles
                remaining_visited, remaining_routes = solve_vrp_for_day(
                    self.master_mat_df,
                    remaining_nodes,
                    day,
                    self.demand_dict,
                    self.penalty_list,
                    self.use_distance,
                    remaining_max_distance,
                    remaining_max_visits
                )

                # Merge results
                visited_nodes.update(remaining_visited)
                for i, vehicle_id in enumerate(available_vehicles):
                    if i in remaining_routes:
                        route_dict[vehicle_id] = remaining_routes[i]
        else:
            # No pre-defined routes, solve VRP normally
            visited_nodes, route_dict = solve_vrp_for_day(
                self.master_mat_df,
                nodes_to_visit,
                day,
                self.demand_dict,
                self.penalty_list,
                self.use_distance,
                self.max_distance,  # Pass max_distance explicitly
                self.max_visits     # Pass max_visits explicitly
            )

        # Get unvisited nodes
        all_po_nodes = self.get_po_node_indices()
        unvisited = all_po_nodes - visited_nodes

        if output_folder:
            # Create job-specific output directories
            os.makedirs(os.path.join(output_folder, 'summaries'), exist_ok=True)
            os.makedirs(os.path.join(output_folder, 'csv'), exist_ok=True)
            os.makedirs(os.path.join(output_folder, 'maps'), exist_ok=True)

            # Print and save summary
            summary_file = os.path.join(output_folder, 'summaries', f"day_{day + 1}_summary.txt")
            print_route_summary(route_dict, self.use_distance, file_path=summary_file)

            # Save detailed route information to CSV
            csv_file = os.path.join(output_folder, 'csv', f"day_{day + 1}_routes.csv")
            save_route_details_to_csv(self.demand_df,route_dict, day, self.use_distance, file_path=csv_file)

            # Visualize routes
            if save_visualization:
                maps_dict = visualize_routes_per_vehicle(
                    self.master_gps_df,
                    route_dict,
                    day,
                    use_distance=self.use_distance
                )

                # Save maps to files
                for vehicle_id, m in maps_dict.items():
                    map_file = os.path.join(output_folder, 'maps', f"day_{day + 1}_vehicle_{vehicle_id}_route.html")
                    m.save(map_file)

            # Save unvisited nodes for next-day processing
            if unvisited:
                self._save_unvisited_nodes_to_csv(unvisited, output_file=os.path.join(output_folder, 'csv', "next_day_demand.csv"))
        else:
            # Use default output directories
            self._create_output_directories()

            # Print and save summary
            summary_file = f"output/summaries/day_{day + 1}_summary.txt"
            print_route_summary(route_dict, self.use_distance, file_path=summary_file)

            # Save detailed route information to CSV
            csv_file = f"output/csv/day_{day + 1}_routes.csv"
            save_route_details_to_csv(self.demand_df,route_dict, day, self.use_distance, file_path=csv_file)

            # Visualize routes
            if save_visualization:
                maps_dict = visualize_routes_per_vehicle(
                    self.master_gps_df,
                    route_dict,
                    day,
                    use_distance=self.use_distance
                )

                # Save maps to files
                os.makedirs("output/maps", exist_ok=True)
                for vehicle_id, m in maps_dict.items():
                    m.save(f"output/maps/day_{day + 1}_vehicle_{vehicle_id}_route.html")

            # Save unvisited nodes for next-day processing
            if unvisited:
                self._save_unvisited_nodes_to_csv(unvisited)

        return visited_nodes, route_dict

    def _create_output_directories(self):
        """
        Create output directories for saving results.
        """
        os.makedirs("output", exist_ok=True)
        os.makedirs("output/summaries", exist_ok=True)
        os.makedirs("output/csv", exist_ok=True)
        os.makedirs("output/maps", exist_ok=True)

    def get_po_node_indices(self):
        """
        Get the indices of nodes in the purchase order (PO) file.

        Returns:
            set: Set of node indices from the PO file
        """
        po_node_indices = []
        for code in self.demand_dict['key']:
            if code in self.master_mat_df.index:
                po_node_indices.append(str(code))

        return set(po_node_indices)

    def _save_unvisited_nodes_to_csv(self, unvisited, output_file=None):
        """
        Save unvisited nodes to a CSV file for next-day processing.

        Args:
            unvisited: Set of unvisited node indices
            output_file: Path to save the CSV file (optional)
        """
        import pandas as pd

        # Get the unvisited node codes
        unvisited_codes = list(unvisited)

        if not unvisited_codes:
            print("No unvisited nodes to save for next day.")
            return

        # Create a DataFrame with the unvisited nodes
        next_day_df = pd.DataFrame()

        # Filter the demand DataFrame to include only unvisited nodes
        if self.demand_df is not None:
            # Convert unvisited_codes to the same type as demand_df['CODE']
            unvisited_codes_set = set(str(code) for code in unvisited_codes)
            next_day_df = self.demand_df[self.demand_df['CODE'].astype(str).isin(unvisited_codes_set)].copy()

        if next_day_df.empty:
            print("Warning: Could not find demand data for unvisited nodes.")
            # Create a simple DataFrame with just the codes
            next_day_df = pd.DataFrame({'CODE': unvisited_codes})

        if 'DEMAND' in next_day_df.columns:
            next_day_df.drop(columns=['DEMAND'], inplace=True)

        # Save to CSV
        if output_file is None:
            # Use default output file
            os.makedirs("output/csv", exist_ok=True)
            output_file = "output/csv/next_day_demand.csv"

        next_day_df.to_csv(output_file, index=False)
        print(f"Saved {len(next_day_df)} unvisited nodes to {output_file} for next-day processing.")

    def update_vehicle_config(self, num_vehicles, max_visits, max_distance, vehicle_routes=None):
        """
        Update the vehicle configuration parameters.

        Args:
            num_vehicles: Number of vehicles
            max_visits: List of maximum visits per vehicle
            max_distance: List of maximum distance per vehicle
            vehicle_routes: Dictionary mapping vehicle_id to route_id
        """
        # Validate inputs
        if len(max_visits) != num_vehicles or len(max_distance) != num_vehicles:
            raise ValueError("Length of max_visits and max_distance must match num_vehicles")

        # Create new lists with the correct length
        new_max_visits = max_visits.copy()
        new_max_distance = max_distance.copy()

        self.max_visits = new_max_visits
        self.max_distance = new_max_distance

        # Update vehicle routes if provided
        if vehicle_routes:
            # Convert vehicle_id keys to integers
            normalized_routes = {}
            for vehicle_id, route_id in vehicle_routes.items():
                try:
                    # Ensure vehicle_id is an integer
                    vehicle_id_int = int(vehicle_id)
                    normalized_routes[vehicle_id_int] = route_id
                except (ValueError, TypeError):
                    print(f"Warning: Invalid vehicle ID {vehicle_id} in vehicle_routes. Skipping.")

            self.vehicle_routes = normalized_routes

        # Update the configuration in the config module
        import vehi_rout.config as config
        config.MAX_VISITS_PER_VEHICLE = new_max_visits
        config.MAX_DISTANCE_PER_VEHICLE = new_max_distance

        print('update_vehicle_config')

    def get_predefined_routes(self):
        """
        Get all pre-defined routes.

        Returns:
            routes: Dictionary of all routes
        """
        return self.route_manager.get_all_routes()

    def assign_route_to_vehicle(self, vehicle_id, route_id):
        """
        Assign a pre-defined route to a vehicle.

        Args:
            vehicle_id: ID of the vehicle
            route_id: ID of the pre-defined route
        """
        try:
            # Ensure vehicle_id is an integer
            vehicle_id_int = int(vehicle_id)

            if route_id:
                self.vehicle_routes[vehicle_id_int] = route_id
            elif vehicle_id_int in self.vehicle_routes:
                del self.vehicle_routes[vehicle_id_int]
        except (ValueError, TypeError):
            print(f"Warning: Invalid vehicle ID {vehicle_id}. Cannot assign route.")

    def get_vehicle_route(self, vehicle_id):
        """
        Get the pre-defined route assigned to a vehicle.

        Args:
            vehicle_id: ID of the vehicle

        Returns:
            route_data: Dictionary containing route information
        """
        try:
            # Ensure vehicle_id is an integer
            vehicle_id_int = int(vehicle_id)
            route_id = self.vehicle_routes.get(vehicle_id_int)

            # Use if-else for clarity
            if route_id:
                return self.route_manager.get_route(route_id)
            else:
                return None
        except (ValueError, TypeError):
            print(f"Warning: Invalid vehicle ID {vehicle_id}. Cannot get route.")
            return None