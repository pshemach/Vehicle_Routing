# """
# Data model for the Vehicle Routing Problem.
# Creates the data model for the solver based on the input data.
# """

# def create_data_model(full_matrix, nodes_to_visit, demand_dict, penalty_list=None,
#                       use_distance=False, max_distance=None, max_visits=None, max_time=None):
#     data = {}

#     node_indices = [0] + [i for i, code in enumerate(full_matrix.index) if code in demand_dict['key']]
#     nodes_to_use = [node_indices[0]] + [i for i in node_indices[1:] if i in nodes_to_visit]

#     data["num_vehicles"] = len(max_distance if use_distance else max_time)
#     data["depot"] = 0  # hardcoded depot here

#     if use_distance:
#         data["distance_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
#         data["max_distance_per_vehicle"] = max_distance
#     else:
#         data["time_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
#         data["max_time_per_vehicle"] = max_time

#     data["demands"] = [0] + [demand_dict.get(full_matrix.index[i], 1) for i in nodes_to_use[1:]]
#     data["node_mapping"] = [full_matrix.index[i] for i in nodes_to_use]
#     data["max_visits_per_vehicle"] = max_visits

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
    data["depot"] = 0  # hardcoded depot

    if use_distance:
        data["distance_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
        data["max_distance_per_vehicle"] = max_distance
    else:
        data["time_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
        data["max_time_per_vehicle"] = max_time

    # Map shop codes for demands and service times
    shop_codes = [full_matrix.index[i] for i in nodes_to_use]

    # Add demands: 0 for depot
    data["demands"] = [0] + [demand_dict.get(sc, 1) for sc in shop_codes[1:]]

    # Add service time: assume 10 mins per demand unit
    data["service_times"] = [0] + [demand_dict.get(sc, 1) * 10 for sc in shop_codes[1:]]

    # Node mapping (code per index)
    data["node_mapping"] = shop_codes
    data["max_visits_per_vehicle"] = max_visits

    # Penalties
    if penalty_list is not None:
        data["penalties"] = [0] + penalty_list
    else:
        data["penalties"] = [0] + [1000] * len(shop_codes[1:])

    return data
