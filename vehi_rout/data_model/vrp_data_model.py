"""
Data model for the Vehicle Routing Problem.
Creates the data model for the solver based on the input data.
"""

def create_data_model(full_matrix, nodes_to_visit, demand_dict, penalty_list=None,
                      use_distance=False, max_distance=None, max_visits=None, max_time=None):
    """
    Create a data model for the Vehicle Routing Problem.

    Args:
        full_matrix: DataFrame containing the distance/time matrix
        nodes_to_visit: List of node indices to visit
        demand_dict: Dictionary containing demand information
        penalty_list: List of penalties for not visiting nodes
        use_distance: Boolean indicating whether to use distance or time
        max_distance: List of maximum distance per vehicle
        max_visits: List of maximum visits per vehicle
        max_time: List of maximum time per vehicle

    Returns:
        data: Dictionary containing the data model
    """
    data = {}

    # Print input parameters for debugging
    print(f"create_data_model called with:")
    print(f"use_distance: {use_distance}")
    print(f"max_distance: {max_distance}")
    print(f"max_visits: {max_visits}")
    print(f"max_time: {max_time}")

    # Map demand_key to indices in the full matrix
    node_indices = [0] + [i for i, code in enumerate(full_matrix.index) if code in demand_dict['key']]
    nodes_to_use = [node_indices[0]] + [i for i in node_indices[1:] if i in nodes_to_visit]

    # Set number of vehicles based on the configuration
    data["num_vehicles"] = len(max_distance if use_distance else max_time)
    data["depot"] = 0  # hardcoded depot here

    # Set up matrix and constraints based on whether we're using distance or time
    if use_distance:
        data["distance_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
        data["max_distance_per_vehicle"] = max_distance
    else:
        data["time_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
        data["max_time_per_vehicle"] = max_time

    # Set up demand and node mapping
    data["demands"] = [0] + [demand_dict.get(full_matrix.index[i], 1) for i in nodes_to_use[1:]]
    data["node_mapping"] = [full_matrix.index[i] for i in nodes_to_use]
    data["max_visits_per_vehicle"] = max_visits

    # Set up penalties for not visiting nodes
    if penalty_list is not None:
        data["penalties"] = [0] + penalty_list
    else:
        # If no penalty list is provided, use a default value
        data["penalties"] = [0] + [1000] * len(nodes_to_use[1:])

    return data
