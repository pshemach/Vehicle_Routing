"""
Data model for the Vehicle Routing Problem.
Creates the data model for the solver based on the input data.
"""

# from vehi_rout.config import (
#     MAX_VISITS_PER_VEHICLE,
#     MAX_TIME_PER_VEHICLE,
#     MAX_DISTANCE_PER_VEHICLE,
#     DEPOT
# )

# def create_data_model(full_matrix, nodes_to_visit, demand_dict, penalty_list=None, use_distance=False):
#     """
#     Create a data model for the Vehicle Routing Problem.

#     Args:
#         full_matrix: DataFrame containing the distance/time matrix
#         nodes_to_visit: List of node indices to visit
#         demand_dict: Dictionary containing demand information
#         penalty_list: List of penalties for not visiting nodes
#         use_distance: Boolean indicating whether to use distance or time

#     Returns:
#         data: Dictionary containing the data model
#     """
#     data = {}

#     # Map demand_key to indices in the full matrix
#     node_indices = [0] + [i for i, code in enumerate(full_matrix.index) if code in demand_dict['key']]
#     nodes_to_use = [node_indices[0]] + [i for i in node_indices[1:] if i in nodes_to_visit]

#     # Set up vehicle parameters
#     data["num_vehicles"] = len(MAX_DISTANCE_PER_VEHICLE if use_distance else MAX_TIME_PER_VEHICLE)
#     data["depot"] = DEPOT

#     # Set up matrix and constraints based on whether we're using distance or time
#     if use_distance:
#         data["distance_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
#         data["max_distance_per_vehicle"] = MAX_DISTANCE_PER_VEHICLE
#     else:
#         data["time_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
#         data["max_time_per_vehicle"] = MAX_TIME_PER_VEHICLE

#     # Set up demand and node mapping
#     data["demands"] = [0] + [demand_dict.get(full_matrix.index[i], 1) for i in nodes_to_use[1:]]
#     data["node_mapping"] = [full_matrix.index[i] for i in nodes_to_use]
#     data["max_visits_per_vehicle"] = MAX_VISITS_PER_VEHICLE

#     # Set up penalties for not visiting nodes
#     if penalty_list is not None:
#         data["penalties"] = [0] + penalty_list
#     else:
#         # If no penalty list is provided, use a default value
#         data["penalties"] = [0] + [1000] * len(nodes_to_use[1:])

#     return data


# import vehi_rout.config as config

# def create_data_model(full_matrix, nodes_to_visit, demand_dict, penalty_list=None, use_distance=False):
#     data = {}

#     node_indices = [0] + [i for i, code in enumerate(full_matrix.index) if code in demand_dict['key']]
#     nodes_to_use = [node_indices[0]] + [i for i in node_indices[1:] if i in nodes_to_visit]

#     data["num_vehicles"] = len(config.MAX_DISTANCE_PER_VEHICLE if use_distance else config.MAX_TIME_PER_VEHICLE)
#     data["depot"] = config.DEPOT

#     if use_distance:
#         data["distance_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
#         data["max_distance_per_vehicle"] = config.MAX_DISTANCE_PER_VEHICLE
#     else:
#         data["time_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
#         data["max_time_per_vehicle"] = config.MAX_TIME_PER_VEHICLE

#     data["demands"] = [0] + [demand_dict.get(full_matrix.index[i], 1) for i in nodes_to_use[1:]]
#     data["node_mapping"] = [full_matrix.index[i] for i in nodes_to_use]
#     data["max_visits_per_vehicle"] = config.MAX_VISITS_PER_VEHICLE

#     if penalty_list is not None:
#         data["penalties"] = [0] + penalty_list
#     else:
#         data["penalties"] = [0] + [1000] * len(nodes_to_use[1:])

#     return data

def create_data_model(full_matrix, nodes_to_visit, demand_dict, penalty_list=None,
                      use_distance=False, max_distance=None, max_visits=None, max_time=None):
    data = {}

    node_indices = [0] + [i for i, code in enumerate(full_matrix.index) if code in demand_dict['key']]
    nodes_to_use = [node_indices[0]] + [i for i in node_indices[1:] if i in nodes_to_visit]

    data["num_vehicles"] = len(max_distance if use_distance else max_time)
    data["depot"] = 0  # hardcoded depot here

    if use_distance:
        data["distance_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
        data["max_distance_per_vehicle"] = max_distance
    else:
        data["time_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
        data["max_time_per_vehicle"] = max_time

    data["demands"] = [0] + [demand_dict.get(full_matrix.index[i], 1) for i in nodes_to_use[1:]]
    data["node_mapping"] = [full_matrix.index[i] for i in nodes_to_use]
    data["max_visits_per_vehicle"] = max_visits

    if penalty_list is not None:
        data["penalties"] = [0] + penalty_list
    else:
        data["penalties"] = [0] + [1000] * len(nodes_to_use[1:])

    return data
