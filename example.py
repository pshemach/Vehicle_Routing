"""
Demo script for the Vehicle Routing Problem.
This script provides a clean implementation with proper UI configuration.
"""

import os
import argparse
import json
from datetime import datetime
from vehi_rout.controller import VRPController
import vehi_rout.config as config

def setup_output_directories():
    """Create output directories for saving results."""
    os.makedirs("output", exist_ok=True)
    os.makedirs("output/summaries", exist_ok=True)
    os.makedirs("output/csv", exist_ok=True)
    os.makedirs("output/maps", exist_ok=True)

def run_vrp_demo(demand_path, matrix_path, gps_path, num_vehicles, max_visits, max_distance,
                 use_distance=True, max_nodes=None, save_visualization=True):
    """
    Run the VRP demo with the specified parameters.

    Args:
        demand_path: Path to the demand file
        matrix_path: Path to the distance/time matrix file
        gps_path: Path to the GPS coordinates file
        num_vehicles: Number of vehicles
        max_visits: List of maximum visits per vehicle
        max_distance: List of maximum distance per vehicle
        use_distance: Boolean indicating whether to use distance or time
        max_nodes: Maximum number of nodes to visit
        save_visualization: Boolean indicating whether to save visualization
    """
    # Create output directories
    setup_output_directories()

    # Initialize controller
    controller = VRPController(use_distance=use_distance)

    # Update vehicle configuration
    controller.update_vehicle_config(
        num_vehicles=num_vehicles,
        max_visits=max_visits,
        max_distance=max_distance
    )

    # Load data
    controller.load_data(
        demand_path=demand_path,
        matrix_path=matrix_path,
        gps_path=gps_path
    )

    # Solve VRP
    visited_nodes, route_dict = controller.solve_single_day(
        day=0,
        max_nodes=max_nodes,
        save_visualization=save_visualization,
        output_folder="output"  # Use the default output folder
    )

    # Print summary
    print("\nRouting Summary:")
    print("-" * 50)
    print(f"Total vehicles: {len(route_dict)}")

    # Calculate total metrics
    total_visits = 0
    total_metric = 0
    metric_name = "distance" if use_distance else "time"
    unit = "km" if use_distance else "mins"

    for vehicle_id, route_info in route_dict.items():
        total_metric += route_info.get(f"route_{metric_name}", 0)
        total_visits += route_info.get("num_visits", 0)

    print(f"Total stops: {total_visits}")
    print(f"Total {metric_name}: {total_metric} {unit}")
    print(f"Total nodes visited: {len(visited_nodes)}")
    print("-" * 50)

    return visited_nodes, route_dict

def main():
    """Main function to parse arguments and run the demo."""
    parser = argparse.ArgumentParser(description='Vehicle Routing Problem Demo')

    # File paths
    parser.add_argument('--demand_path', type=str, default='data/test.csv',
                        help='Path to the demand file')
    parser.add_argument('--matrix_path', type=str, default='data/master/osrm_distance_matrix.csv',
                        help='Path to the distance/time matrix file')
    parser.add_argument('--gps_path', type=str, default='data/master/master_gps.csv',
                        help='Path to the GPS coordinates file')

    # Vehicle configuration
    parser.add_argument('--num_vehicles', type=int, default=8,
                        help='Number of vehicles')
    parser.add_argument('--max_visits', type=int, nargs='+', default=[12, 12, 12, 12, 12, 12, 12, 12],
                        help='Maximum visits per vehicle')
    parser.add_argument('--max_distance', type=int, nargs='+', default=[500, 500, 500, 500, 500, 500, 500, 500],
                        help='Maximum distance per vehicle')

    # Solver options
    parser.add_argument('--use_time', action='store_true',
                        help='Use time instead of distance')
    parser.add_argument('--max_nodes', type=int, default=None,
                        help='Maximum number of nodes to visit')
    parser.add_argument('--no_visualization', action='store_true',
                        help='Disable visualization')

    args = parser.parse_args()

    # Validate vehicle configuration
    if len(args.max_visits) != args.num_vehicles:
        parser.error(f"Length of max_visits ({len(args.max_visits)}) must match num_vehicles ({args.num_vehicles})")

    if len(args.max_distance) != args.num_vehicles:
        parser.error(f"Length of max_distance ({len(args.max_distance)}) must match num_vehicles ({args.num_vehicles})")

    # Run the demo
    run_vrp_demo(
        demand_path=args.demand_path,
        matrix_path=args.matrix_path,
        gps_path=args.gps_path,
        num_vehicles=args.num_vehicles,
        max_visits=args.max_visits,
        max_distance=args.max_distance,
        use_distance=not args.use_time,
        max_nodes=args.max_nodes,
        save_visualization=not args.no_visualization
    )

if __name__ == '__main__':
    main()