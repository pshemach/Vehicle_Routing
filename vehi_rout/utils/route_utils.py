"""
Route utilities for the Vehicle Routing Problem.
"""

import numpy as np

def sort_nodes_by_distance(matrix):
    """
    Sort nodes by distance from the depot.

    Args:
        matrix: Distance matrix

    Returns:
        list: List of node indices sorted by distance from the depot
    """
    distances = [(node, matrix[0][node]) for node in range(1, len(matrix))]
    return [node for node, _ in sorted(distances, key=lambda x: x[1])]

def distribute_nodes_to_vehicles(nodes, num_vehicles):
    """
    Distribute nodes evenly among vehicles.

    Args:
        nodes: List of node indices
        num_vehicles: Number of vehicles

    Returns:
        dict: Dictionary mapping vehicle indices to lists of node indices
    """
    # Create empty lists for each vehicle
    vehicle_nodes = {i: [] for i in range(num_vehicles)}

    # Sort nodes by distance from depot (assuming nodes are already sorted)
    sorted_nodes = nodes.copy()

    # Distribute nodes in a round-robin fashion
    for i, node in enumerate(sorted_nodes):
        vehicle_id = i % num_vehicles
        vehicle_nodes[vehicle_id].append(node)

    return vehicle_nodes