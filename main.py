"""
Main script to run the Vehicle Routing Problem solution.
"""

import argparse
from vehi_rout.controller import VRPController

def main():
    """Main function to run the VRP solution."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Vehicle Routing Problem Solver')
    parser.add_argument('--demand', type=str, default='data/orders/03-03-2025-PO.csv',
                        help='Path to the demand file')
    parser.add_argument('--matrix', type=str, default='data/master/osrm_distance_matrix.csv',
                        help='Path to the distance/time matrix file')
    parser.add_argument('--gps', type=str, default='data/master/master_gps.csv',
                        help='Path to the GPS coordinates file')
    parser.add_argument('--use-time', action='store_true',
                        help='Use time instead of distance')
    parser.add_argument('--multi-day', action='store_true',
                        help='Solve for multiple days')
    parser.add_argument('--days', type=int, default=None,
                        help='Number of days to plan')
    parser.add_argument('--max-nodes', type=int, default=None,
                        help='Maximum number of nodes to visit')
    parser.add_argument('--save-viz', action='store_true',
                        help='Save visualization')

    args = parser.parse_args()

    # Create controller
    controller = VRPController(use_distance=not args.use_time)

    # Load data
    controller.load_data(args.demand, args.matrix, args.gps)

    # Solve VRP
    if args.multi_day:
        all_visited_nodes, all_route_dicts = controller.solve_multi_day(
            total_days=args.days,
            max_nodes=args.max_nodes,
            save_visualization=args.save_viz
        )

        # Print summary
        print("\n=== Multi-Day Summary ===")
        total_nodes = sum(len(visited_nodes) for visited_nodes in all_visited_nodes)
        print(f"Total nodes visited across all days: {total_nodes}")

        # Print unvisited nodes
        all_visited = set()
        for visited in all_visited_nodes:
            all_visited.update(visited)

        # Get all nodes from the demand data (PO file) instead of master data
        all_po_nodes = controller.get_po_node_indices()
        unvisited = all_po_nodes - all_visited

        if unvisited:
            print(f"Unvisited nodes: {len(unvisited)}")
            print(f"Unvisited node codes: {[controller.master_mat_df.index[i] for i in unvisited]}")
    else:
        visited_nodes, route_dict = controller.solve_single_day(
            day=0,
            max_nodes=args.max_nodes,
            save_visualization=args.save_viz
        )

        # Print summary
        print("\n=== Single-Day Summary ===")
        print(f"Total nodes visited: {len(visited_nodes)}")

        # Print unvisited nodes
        # Get all nodes from the demand data (PO file) instead of master data
        all_po_nodes = controller.get_po_node_indices()
        unvisited = all_po_nodes - visited_nodes

        if unvisited:
            print(f"Unvisited nodes: {len(unvisited)}")
            print(f"Unvisited node codes: {[controller.master_mat_df.index[i] for i in unvisited]}")

if __name__ == '__main__':
    main()
