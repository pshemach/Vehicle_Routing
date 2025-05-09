"""
Controller module for the Vehicle Routing Problem.
Orchestrates the entire process of solving the VRP.
"""

import pandas as pd
from datetime import datetime
import os

from vehi_rout.config import (
    TOTAL_DAYS,
    DISTANCE_BASE_PENALTY,
    TIME_BASE_PENALTY
)
from vehi_rout.utils.data_utils import (
    load_matrix_df,
    load_df,
    get_demand_df,
    update_demand_dic
)
from vehi_rout.utils.helper_utils import (
    get_penalty_list,
    get_values_not_in_second_list
)
from vehi_rout.utils.route_utils import sort_nodes_by_distance
from vehi_rout.utils.visualization import (
    visualize_routes_per_vehicle,
    print_route_summary,
    save_route_details_to_csv
)
from vehi_rout.solver.vrp_solver import (
    solve_vrp_for_day,
    solve_multi_day_vrp
)

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


    def solve_single_day(self, day=0, max_nodes=None, save_visualization=False):
        """
        Solve the VRP for a single day.

        Args:
            day: Day index (0-based)
            max_nodes: Maximum number of nodes to visit
            save_visualization: Boolean indicating whether to save visualization

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

        # Solve VRP
        visited_nodes, route_dict = solve_vrp_for_day(
            self.master_mat_df,
            nodes_to_visit,
            day,
            self.demand_dict,
            self.penalty_list,
            self.use_distance
        )

        # Create output directories
        self._create_output_directories()

        # Print and save summary
        summary_file = f"output/summaries/day_{day + 1}_summary.txt"
        print_route_summary(route_dict, self.use_distance, file_path=summary_file)

        # Save detailed route information to CSV
        csv_file = f"output/csv/day_{day + 1}_routes.csv"
        save_route_details_to_csv(self.demand_df, route_dict, day, self.use_distance, file_path=csv_file)

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
        all_po_nodes = self.get_po_node_indices()
        unvisited = all_po_nodes - visited_nodes
        self._save_unvisited_nodes_to_csv(unvisited)

        return visited_nodes, route_dict

    def solve_multi_day(self, total_days=None, max_nodes=None, save_visualization=False):
        """
        Solve the VRP for multiple days.

        Args:
            total_days: Number of days to plan
            max_nodes: Maximum number of nodes to visit per day
            save_visualization: Boolean indicating whether to save visualization

        Returns:
            all_visited_nodes: List of sets of visited node indices for each day
            all_route_dicts: List of dictionaries containing route information for each day
        """
        if self.demand_df is None or self.master_mat_df is None or self.master_gps_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")

        # Use default total days if not specified
        if total_days is None:
            total_days = TOTAL_DAYS

        # Solve multi-day VRP
        all_visited_nodes, all_route_dicts = solve_multi_day_vrp(
            self.master_mat_df,
            self.demand_dict,
            total_days,
            self.base_penalty,
            self.use_distance,
            current_date=None,
            max_nodes_per_day=max_nodes
        )

        # Create output directories
        self._create_output_directories()

        # Create a combined CSV for all days
        combined_csv_path = f"output/csv/all_days_routes.csv"
        import csv
        with open(combined_csv_path, 'w', newline='') as csvfile:
            metric_name = "distance" if self.use_distance else "time"
            unit = "km" if self.use_distance else "mins"
            fieldnames = ['Day', 'Vehicle', 'Stops', f'{metric_name.capitalize()} ({unit})',
                         f'Max {metric_name.capitalize()} ({unit})', 'Within Limit', 'Route']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

        # Process each day
        for day, route_dict in enumerate(all_route_dicts):
            print(f"\n=== Day {day + 1} ===")

            # Print and save summary
            summary_file = f"output/summaries/day_{day + 1}_summary.txt"
            print_route_summary(route_dict, self.use_distance, file_path=summary_file)

            # Save detailed route information to CSV
            csv_file = f"output/csv/day_{day + 1}_routes.csv"
            save_route_details_to_csv(route_dict, day, self.use_distance, file_path=csv_file)

            # Append to combined CSV
            self._append_to_combined_csv(route_dict, day, combined_csv_path)

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
                    m.save(f"output/maps/day_{day + 1}_vehicle_{vehicle_id}_route.html")

        # Create a multi-day summary
        self._save_multi_day_summary(all_route_dicts, all_visited_nodes)

        return all_visited_nodes, all_route_dicts

    def _append_to_combined_csv(self, route_dict, day, file_path):
        """
        Append route information to a combined CSV file.

        Args:
            route_dict: Dictionary containing route information for each vehicle
            day: Day index (0-based)
            file_path: Path to the CSV file
        """
        import csv

        metric_name = "distance" if self.use_distance else "time"
        unit = "km" if self.use_distance else "mins"

        with open(file_path, 'a', newline='') as csvfile:
            fieldnames = ['Day', 'Vehicle', 'Stops', f'{metric_name.capitalize()} ({unit})',
                         f'Max {metric_name.capitalize()} ({unit})', 'Within Limit', 'Route']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

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

    def _save_multi_day_summary(self, all_route_dicts, all_visited_nodes):
        """
        Save a summary of the multi-day routing and create a next-day demand file.

        Args:
            all_route_dicts: List of dictionaries containing route information for each day
            all_visited_nodes: List of sets of visited node indices for each day
        """
        metric_name = "distance" if self.use_distance else "time"
        unit = "km" if self.use_distance else "mins"

        # Calculate total metrics
        total_metric = 0
        total_visits = 0

        for route_dict in all_route_dicts:
            for vehicle_id, route_info in route_dict.items():
                total_metric += route_info.get(f"route_{metric_name}", 0)
                total_visits += route_info.get("num_visits", 0)

        # Calculate visited and unvisited nodes
        all_visited = set()
        for visited in all_visited_nodes:
            all_visited.update(visited)

        # Get all nodes from the demand data (PO file) instead of master data
        all_po_nodes = self.get_po_node_indices()
        unvisited = all_po_nodes - all_visited

        # Create summary lines
        summary_lines = []
        summary_lines.append(f"Multi-Day Routing Summary")
        summary_lines.append(f"-" * 50)
        summary_lines.append(f"Total days: {len(all_route_dicts)}")
        summary_lines.append(f"Total vehicles: {len(all_route_dicts[0]) if all_route_dicts else 0}")
        summary_lines.append(f"Total stops: {total_visits}")
        summary_lines.append(f"Total {metric_name}: {total_metric} {unit}")
        summary_lines.append(f"Total nodes visited: {len(all_visited)}")
        summary_lines.append(f"Total nodes unvisited: {len(unvisited)}")
        summary_lines.append(f"-" * 50)

        # Save to file
        summary_file = "output/summaries/multi_day_summary.txt"
        with open(summary_file, 'w') as f:
            for line in summary_lines:
                f.write(line + '\n')

            # Add unvisited nodes if any
            if unvisited:
                f.write(f"\nUnvisited nodes:\n")
                unvisited_codes = [self.master_mat_df.index[i] for i in unvisited if i < len(self.master_mat_df.index)]
                for i, code in enumerate(unvisited_codes):
                    f.write(f"{code}")
                    if (i + 1) % 10 == 0:  # 10 codes per line
                        f.write("\n")
                    else:
                        f.write(", ")

        print(f"Multi-day summary saved to {summary_file}")

        # Save unvisited nodes to a CSV file for next-day processing
        self._save_unvisited_nodes_to_csv(unvisited)

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
                idx = self.master_mat_df.index.get_loc(code)
                po_node_indices.append(str(code))

        return set(po_node_indices)

    def _save_unvisited_nodes_to_csv(self, unvisited):
        """
        Save unvisited nodes to a CSV file for next-day processing.

        Args:
            unvisited: Set of unvisited node indices
        """
        import pandas as pd

        # Get the unvisited node codes
        # unvisited_codes = [self.master_mat_df.index[i] for i in unvisited if i < len(self.master_mat_df.index)]
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
        next_day_file = "output/csv/next_day_demand.csv"
        next_day_df.to_csv(next_day_file, index=False)
        print(f"Saved {len(next_day_df)} unvisited nodes to {next_day_file} for next-day processing.")

    def update_vehicle_config(self, num_vehicles, max_visits, max_distance):
        """
        Update the vehicle configuration parameters.

        Args:
            num_vehicles: Number of vehicles
            max_visits: List of maximum visits per vehicle
            max_distance: List of maximum distance per vehicle
        """
        # Validate inputs
        if len(max_visits) != num_vehicles or len(max_distance) != num_vehicles:
            raise ValueError("Length of max_visits and max_distance must match num_vehicles")
    


        # Create new lists with the correct length
        new_max_visits = max_visits.copy()
        new_max_distance = max_distance.copy()
        
        self.max_distance = new_max_distance
        self.max_visits = new_max_visits

        # Update the configuration in the config module
        import vehi_rout.config as config
        config.MAX_VISITS_PER_VEHICLE = new_max_visits
        config.MAX_DISTANCE_PER_VEHICLE = new_max_distance

        print(f"Updated vehicle configuration:")
        print(f"Number of vehicles: {num_vehicles}")
        print(f"Max visits per vehicle: {new_max_visits}")
        print(f"Max distance per vehicle: {new_max_distance}")
