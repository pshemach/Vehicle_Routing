"""
Example script to demonstrate how to use the vehicle routing solution.

This script shows how to use the vehicle routing solution to solve both single-day
and multi-day routing problems. It also demonstrates how to save route summaries,
detailed route information, and visualizations.
"""

from vehi_rout.controller import VRPController

def main():
    """Main function to demonstrate the vehicle routing solution."""
    # Create controller (using distance by default)
    controller = VRPController(use_distance=True)

    # Load data
    controller.load_data(
        demand_path='data/orders/03-03-2025-PO.csv',
        matrix_path='data/master/osrm_distance_matrix.csv',
        gps_path='data/master/master_gps.csv'
    )

    # Example 1: Solve for a single day with limited nodes
    print("\n=== Example 1: Single Day Routing ===")
    visited_nodes, route_dict = controller.solve_single_day(
        day=0,
        max_nodes=300,  # Limit to 300 nodes
        save_visualization=True
    )

    print("\nSingle day routing completed!")
    print("The following files have been generated:")
    print("  - Route summary: output/summaries/day_1_summary.txt")
    print("  - Detailed route information: output/csv/day_1_routes.csv")
    print("  - Route visualizations: output/maps/day_1_vehicle_X_route.html")

    # Example 2: Solve for multiple days
    print("\n=== Example 2: Multi-Day Routing ===")
    all_visited_nodes, all_route_dicts = controller.solve_multi_day(
        total_days=3,  # Plan for 3 days
        max_nodes=300,  # Limit to 300 nodes per day
        save_visualization=True
    )

    print("\nMulti-day routing completed!")
    print("The following files have been generated:")
    print("  - Daily route summaries: output/summaries/day_X_summary.txt")
    print("  - Multi-day summary: output/summaries/multi_day_summary.txt")
    print("  - Daily route details: output/csv/day_X_routes.csv")
    print("  - Combined route details: output/csv/all_days_routes.csv")
    print("  - Route visualizations: output/maps/day_X_vehicle_Y_route.html")

    # Print summary of multi-day routing
    print("\n=== Multi-Day Summary ===")
    total_nodes = sum(len(visited) for visited in all_visited_nodes)
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
        print(f"Unvisited node codes: {[controller.master_mat_df.index[i] for i in unvisited if i < len(controller.master_mat_df.index)]}")

if __name__ == '__main__':
    main()
