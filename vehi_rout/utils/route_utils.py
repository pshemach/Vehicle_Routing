"""
Route utilities for the Vehicle Routing Problem.
"""

# No imports needed for this module

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