"""
Controller module for the Vehicle Routing Problem.
Orchestrates the entire process of solving the VRP.
"""

import pandas as pd
from datetime import datetime
import os
import json

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
)
from vehi_rout.utils.route_utils import sort_nodes_by_distance
from vehi_rout.utils.visualization import (
    visualize_routes_per_vehicle,
    print_route_summary,
    save_route_details_to_csv
)
from vehi_rout.solver.vrp_solver import (
    solve_vrp_for_day,
)
from vehi_rout.solver.vrp_duration_solver import (
    solve_vrp_time
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
        
        self.vehicle_routes = {}
        self.predefined_routes = []

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
        
        if hasattr(self, 'vehicle_routes') and self.vehicle_routes:
            print(f"Loaded vehicle_routes for predefined routes: {self.vehicle_routes}")
        if hasattr(self, 'predefined_routes') and self.predefined_routes:
            print(f"Loaded {len(self.predefined_routes)} predefined route definitions.")



    # def solve_single_day(self, day=0, max_nodes=None, save_visualization=False,
    #                  geo_constraints=None, order_time_window=None,
    #                  order_groups=None, priority_orders=None, vehicle_constraints=None):
    #     """
    #     Solve the VRP for a single day.

    #     Args:
    #         day: Day index (0-based)
    #         max_nodes: Maximum number of nodes to visit
    #         save_visualization: Boolean indicating whether to save visualization

    #     Returns:
    #         visited_nodes: Set of visited node indices
    #         route_dict: Dictionary containing route information for each vehicle
    #     """
    #     if self.demand_df is None or self.master_mat_df is None or self.master_gps_df is None:
    #         raise ValueError("Data not loaded. Call load_data() first.")

    #     # Get nodes to visit
    #     all_nodes = list(range(1, len(self.master_mat_df)))

    #     # Sort nodes by distance from depot
    #     sorted_nodes = sort_nodes_by_distance(self.master_mat_df.values)

    #     # Limit the number of nodes if specified
    #     if max_nodes is not None and max_nodes < len(sorted_nodes):
    #         nodes_to_visit = sorted(sorted_nodes[:max_nodes])
    #     else:
    #         nodes_to_visit = all_nodes

    #     # Solve VRP
    #     visited_nodes, route_dict = solve_vrp_for_day(
    #             self.master_mat_df,
    #             nodes_to_visit,
    #             day,
    #             self.demand_dict,
    #             self.penalty_list,
    #             self.use_distance,
    #             geo_constraints=geo_constraints,
    #             order_time_window=order_time_window,
    #             order_groups=order_groups,
    #             priority_orders=priority_orders,
    #             vehicle_constraints=vehicle_constraints
    #         )

    #     # Create output directories
    #     self._create_output_directories()

    #     # Print and save summary
    #     summary_file = f"output/summaries/day_{day + 1}_summary.txt"
    #     print_route_summary(route_dict, self.use_distance, file_path=summary_file)

    #     # Save detailed route information to CSV
    #     csv_file = f"output/csv/day_{day + 1}_routes.csv"
    #     save_route_details_to_csv(self.demand_df, route_dict, day, self.use_distance, file_path=csv_file)

    #     # Save route_dict as JSON for API use
    #     job_id = None
    #     # Try to get job_id from environment or context if available
    #     if hasattr(self, 'job_id'):
    #         job_id = self.job_id
    #     if not job_id:
    #         # Fallback: try to extract from output path
    #         import re
    #         match = re.search(r'output/(.*?)/', csv_file)
    #         if match:
    #             job_id = match.group(1)
    #         else:
    #             job_id = 'default'
    #     os.makedirs(f'output/{job_id}', exist_ok=True)
    #     with open(f'output/{job_id}/route_dict_day_{day+1}.json', 'w') as f:
    #         json.dump(route_dict, f, default=str)

    #     # Visualize routes
    #     if save_visualization:
    #         maps_dict = visualize_routes_per_vehicle(
    #             self.master_gps_df,
    #             route_dict,
    #             day,
    #             use_distance=self.use_distance
    #         )

    #         # Save maps to files
    #         os.makedirs("output/maps", exist_ok=True)
    #         for vehicle_id, m in maps_dict.items():
    #             m.save(f"output/maps/day_{day + 1}_vehicle_{vehicle_id}_route.html")

    #     # Save unvisited nodes for next-day processing
    #     all_po_nodes = self.get_po_node_indices()
    #     unvisited = all_po_nodes - visited_nodes
    #     self._save_unvisited_nodes_to_csv(unvisited)

    #     return visited_nodes, route_dict
    
    def solve_single_day(self, day=0, save_visualization=False,
                     geo_constraints=None, order_time_window=None,
                     order_groups=None, priority_orders=None, vehicle_constraints=None):
        """
        Solve the VRP for a single day.
        If predefined routes are assigned, solve them first, then run normal VRP for remaining vehicles.
        """
        if self.demand_df is None or self.master_mat_df is None or self.master_gps_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")

        # --- Step 0: Prepare nodes ---
        all_nodes = list(range(1, len(self.master_mat_df)))
        sorted_nodes = sort_nodes_by_distance(self.master_mat_df.values)
        # nodes_to_visit = sorted_nodes[:max_nodes] if max_nodes and max_nodes < len(sorted_nodes) else all_nodes
        nodes_to_visit = sorted_nodes
        visited_nodes = set()
        route_dict = {}

        used_vehicles = set()

        # --- Step 1: Handle predefined routes first ---
        if self.vehicle_routes and self.predefined_routes:
            predefined_route_map = {r["id"]: r for r in self.predefined_routes}

            for vehicle_id, route_id in self.vehicle_routes.items():
                try:
                    vehicle_id_int = int(vehicle_id)
                except:
                    print(f"Invalid vehicle_id in vehicle_routes: {vehicle_id}")
                    continue

                route_def = predefined_route_map.get(route_id)
                if not route_def:
                    print(f"No predefined route found for id {route_id}")
                    continue

                shop_codes = route_def.get("codes", [])
                print(f"Shop Code: {shop_codes}")
                demand_codes = set(self.demand_dict['key'])
                print(f"Demand Dict: {demand_codes}")
                filtered_codes = [c for c in shop_codes if c in demand_codes]

                if not filtered_codes:
                    print(f"Predefined route {route_id} has no active demand")
                    continue

                # Convert shop codes to node indices
                node_indices = [self.master_mat_df.index.get_loc(code) for code in filtered_codes]

                print(f"Solving predefined route for vehicle {vehicle_id_int} with nodes {filtered_codes}")

                # Temporarily set config for single vehicle
                import vehi_rout.config as config
                old_max_visits = config.MAX_VISITS_PER_VEHICLE
                old_max_distance = config.MAX_DISTANCE_PER_VEHICLE

                config.MAX_VISITS_PER_VEHICLE = [self.max_visits[vehicle_id_int]]
                config.MAX_DISTANCE_PER_VEHICLE = [self.max_distance[vehicle_id_int]]
                
                if self.use_distance == True:
                    # Solve VRP for just this vehicle (TSP-like)
                    visited, route = solve_vrp_for_day(
                        self.master_mat_df,
                        node_indices,  # include depot
                        day,
                        self.demand_dict,
                        self.penalty_list,
                        self.use_distance,
                        geo_constraints=geo_constraints,
                        order_time_window=order_time_window,
                        order_groups=order_groups,
                        priority_orders=priority_orders,
                        vehicle_constraints=vehicle_constraints
                    )
                    
                else:
                    visited, route = solve_vrp_time(
                        self.master_mat_df,
                        node_indices,  # include depot
                        day,
                        self.demand_dict,
                        self.penalty_list,
                        self.use_distance,
                        geo_constraints=geo_constraints,
                        order_time_window=order_time_window,
                        order_groups=order_groups,
                        priority_orders=priority_orders,
                        vehicle_constraints=vehicle_constraints
                    )

                # Restore config
                config.MAX_VISITS_PER_VEHICLE = old_max_visits
                config.MAX_DISTANCE_PER_VEHICLE = old_max_distance

                if route:
                    # Only one vehicle in this mini-VRP
                    route_dict[vehicle_id_int] = list(route.values())[0]
                    visited_nodes.update(visited)
                    used_vehicles.add(vehicle_id_int)

        # --- Step 2: Solve normal VRP for remaining vehicles ---
        remaining_nodes = [n for n in nodes_to_visit if n not in visited_nodes]
        available_vehicles = [i for i in range(len(self.max_visits)) if i not in used_vehicles]

        if remaining_nodes and available_vehicles:
            remaining_max_visits = [self.max_visits[i] for i in available_vehicles]
            remaining_max_distance = [self.max_distance[i] for i in available_vehicles]

            import vehi_rout.config as config
            old_max_visits = config.MAX_VISITS_PER_VEHICLE
            old_max_distance = config.MAX_DISTANCE_PER_VEHICLE
            config.MAX_VISITS_PER_VEHICLE = remaining_max_visits
            config.MAX_DISTANCE_PER_VEHICLE = remaining_max_distance
            if self.use_distance == True:
                rem_visited, rem_routes = solve_vrp_for_day(
                    self.master_mat_df,
                    remaining_nodes,
                    day,
                    self.demand_dict,
                    self.penalty_list,
                    self.use_distance,
                    geo_constraints=geo_constraints,
                    order_time_window=order_time_window,
                    order_groups=order_groups,
                    priority_orders=priority_orders,
                    vehicle_constraints=vehicle_constraints
                )
                
            else:
                rem_visited, rem_routes = solve_vrp_time(
                self.master_mat_df,
                remaining_nodes,
                day,
                self.demand_dict,
                self.penalty_list,
                self.use_distance,
                geo_constraints=geo_constraints,
                order_time_window=order_time_window,
                order_groups=order_groups,
                priority_orders=priority_orders,
                vehicle_constraints=vehicle_constraints
            )

            config.MAX_VISITS_PER_VEHICLE = old_max_visits
            config.MAX_DISTANCE_PER_VEHICLE = old_max_distance

            visited_nodes.update(rem_visited)
            for idx, veh_id in enumerate(available_vehicles):
                if idx in rem_routes:
                    route_dict[veh_id] = rem_routes[idx]

        # --- Step 3: Create output directories ---
        self._create_output_directories()

        # Print and save summary
        summary_file = f"output/summaries/day_{day + 1}_summary.txt"
        print_route_summary(route_dict, self.use_distance, file_path=summary_file)

        # Save detailed route information to CSV
        csv_file = f"output/csv/day_{day + 1}_routes.csv"
        save_route_details_to_csv(self.demand_df, route_dict, day, self.use_distance, file_path=csv_file)

        # Save route_dict as JSON for API use
        job_id = getattr(self, 'job_id', 'default')
        os.makedirs(f'output/{job_id}', exist_ok=True)
        with open(f'output/{job_id}/route_dict_day_{day+1}.json', 'w') as f:
            json.dump(route_dict, f, default=str)

        # --- Step 4: Visualize ---
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

        # --- Step 5: Save unvisited nodes ---
        all_po_nodes = self.get_po_node_indices()
        unvisited = all_po_nodes - visited_nodes
        self._save_unvisited_nodes_to_csv(unvisited)

        return visited_nodes, route_dict



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

    def get_route_orders(self, day, vehicle):
        """
        Get orders assigned to a specific route.

        Args:
            day: Day index (0-based)
            vehicle: Vehicle index

        Returns:
            List of Order objects containing order information
        """
        if not hasattr(self, 'all_route_dicts') or day >= len(self.all_route_dicts):
            return []
            
        route_dict = self.all_route_dicts[day]
        if vehicle not in route_dict:
            return []
            
        route = route_dict[vehicle]['route']
        orders = []
        
        for node in route:
            if node == 0:  # Skip depot
                continue
                
            # Get order information from demand_df
            order_info = self.demand_df[self.demand_df['CODE'] == str(node)].iloc[0]
            orders.append({
                'id': str(node),
                'location': order_info['LOCATION'],
                'volume': float(order_info['VOLUME']),
                'priority': int(order_info.get('PRIORITY', 0))
            })
            
        return orders

    def get_available_orders(self, day):
        """
        Get orders that are not assigned to any route for the given day.

        Args:
            day: Day index (0-based)

        Returns:
            List of Order objects containing order information
        """
        if not hasattr(self, 'all_route_dicts') or day >= len(self.all_route_dicts):
            return []
            
        # Get all nodes assigned to routes for this day
        assigned_nodes = set()
        route_dict = self.all_route_dicts[day]
        
        for vehicle_routes in route_dict.values():
            assigned_nodes.update(vehicle_routes['route'])
            
        # Remove depot from assigned nodes
        assigned_nodes.discard(0)
        
        # Get all PO nodes
        all_po_nodes = self.get_po_node_indices()
        
        # Get unassigned nodes
        unassigned_nodes = all_po_nodes - assigned_nodes
        
        # Convert nodes to order information
        orders = []
        for node in unassigned_nodes:
            # Get order information from demand_df
            order_info = self.demand_df[self.demand_df['CODE'] == str(node)].iloc[0]
            orders.append({
                'id': str(node),
                'location': order_info['LOCATION'],
                'volume': float(order_info['VOLUME']),
                'priority': int(order_info.get('PRIORITY', 0))
            })
            
        return orders

    def add_order_to_route(self, order_id, day, vehicle):
        """
        Add an order to a specific route.

        Args:
            order_id: Order ID to add
            day: Day index (0-based)
            vehicle: Vehicle index
        """
        if not hasattr(self, 'all_route_dicts') or day >= len(self.all_route_dicts):
            raise ValueError(f"Invalid day: {day}")
            
        route_dict = self.all_route_dicts[day]
        if vehicle not in route_dict:
            raise ValueError(f"Invalid vehicle: {vehicle}")
            
        # Convert order_id to node index
        node = int(order_id)
        
        # Check if order exists
        if not self.demand_df[self.demand_df['CODE'] == str(node)].shape[0]:
            raise ValueError(f"Order {order_id} not found")
            
        # Add node to route
        route = route_dict[vehicle]['route']
        if node not in route:
            # Insert before the last depot visit
            route.insert(-1, node)
            
            # Update route metrics
            self._update_route_metrics(route_dict[vehicle])

    def remove_order_from_route(self, order_id, day, vehicle):
        """
        Remove an order from a specific route.

        Args:
            order_id: Order ID to remove
            day: Day index (0-based)
            vehicle: Vehicle index
        """
        if not hasattr(self, 'all_route_dicts') or day >= len(self.all_route_dicts):
            raise ValueError(f"Invalid day: {day}")
            
        route_dict = self.all_route_dicts[day]
        if vehicle not in route_dict:
            raise ValueError(f"Invalid vehicle: {vehicle}")
            
        # Convert order_id to node index
        node = int(order_id)
        
        # Remove node from route
        route = route_dict[vehicle]['route']
        if node in route:
            route.remove(node)
            
            # Update route metrics
            self._update_route_metrics(route_dict[vehicle])

    def update_route_orders(self, order_ids, day, vehicle):
        """
        Update the orders in a specific route.

        Args:
            order_ids: List of order IDs for the route
            day: Day index (0-based)
            vehicle: Vehicle index
        """
        if not hasattr(self, 'all_route_dicts') or day >= len(self.all_route_dicts):
            raise ValueError(f"Invalid day: {day}")
            
        route_dict = self.all_route_dicts[day]
        if vehicle not in route_dict:
            raise ValueError(f"Invalid vehicle: {vehicle}")
            
        # Convert order IDs to node indices
        nodes = [int(order_id) for order_id in order_ids]
        
        # Validate all nodes exist
        for node in nodes:
            if not self.demand_df[self.demand_df['CODE'] == str(node)].shape[0]:
                raise ValueError(f"Order {node} not found")
                
        # Update route with new nodes
        route = route_dict[vehicle]['route']
        route.clear()
        route.append(0)  # Start at depot
        route.extend(nodes)
        route.append(0)  # End at depot
        
        # Update route metrics
        self._update_route_metrics(route_dict[vehicle])

    def regenerate_route_visualization(self, day, vehicle):
        """
        Regenerate the visualization for a specific route.

        Args:
            day: Day index (0-based)
            vehicle: Vehicle index
        """
        if not hasattr(self, 'all_route_dicts') or day >= len(self.all_route_dicts):
            raise ValueError(f"Invalid day: {day}")
            
        route_dict = self.all_route_dicts[day]
        if vehicle not in route_dict:
            raise ValueError(f"Invalid vehicle: {vehicle}")
            
        # Create single vehicle route dictionary
        vehicle_route_dict = {vehicle: route_dict[vehicle]}
        
        # Generate and save map
        maps_dict = visualize_routes_per_vehicle(
            self.master_gps_df,
            vehicle_route_dict,
            day,
            use_distance=self.use_distance
        )
        
        # Save map to file
        os.makedirs("output/maps", exist_ok=True)
        for vid, m in maps_dict.items():
            m.save(f"output/maps/day_{day + 1}_vehicle_{vid}_route.html")
            
        # Update route summary
        summary_file = f"output/summaries/day_{day + 1}_summary.txt"
        print_route_summary(route_dict, self.use_distance, file_path=summary_file)
        
        # Update route details CSV
        csv_file = f"output/csv/day_{day + 1}_routes.csv"
        save_route_details_to_csv(self.demand_df, route_dict, day, self.use_distance, file_path=csv_file)

    def _update_route_metrics(self, route_info):
        """
        Update the metrics for a route after modification.

        Args:
            route_info: Dictionary containing route information
        """
        route = route_info['route']
        
        # Calculate total distance/time
        total = 0
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]
            total += self.master_mat_df.iloc[from_node, to_node]
            
        # Update route information
        route_info['total_distance' if self.use_distance else 'total_time'] = total
        route_info['stops'] = len(route) - 2  # Subtract depot visits
        route_info['within_limit'] = total <= route_info['max_distance' if self.use_distance else 'max_time']
