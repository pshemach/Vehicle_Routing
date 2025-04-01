from utils.helper_utils import get_penalty_list
from constant import BASE_PENALTY, TOTAL_DAYS, MAX_VISITS_PER_VEHICLE, MAX_TIME_PER_VEHICLE

def create_data_model(full_matrix, nodes_to_visit, demand_dict):
    data = {}
    # Map demand_key to indices in the full matrix
    node_indices = [0] + [i for i, code in enumerate(full_matrix.index) if code in demand_dict['key']]
    nodes_to_use = [node_indices[0]] + [i for i in node_indices[1:] if i in nodes_to_visit]
    data["time_matrix"] = [[full_matrix.iloc[i][j] for j in nodes_to_use] for i in nodes_to_use]
    data["num_vehicles"] = len(MAX_VISITS_PER_VEHICLE)
    data["depot"] = 0
    data["max_time_per_vehicle"] = MAX_TIME_PER_VEHICLE
    data["max_visits_per_vehicle"] = MAX_VISITS_PER_VEHICLE
    data["demands"] = [0] + [demand_dict.get(full_matrix.index[i], 1) for i in nodes_to_use[1:]]
    data["node_mapping"] = [full_matrix.index[i] for i in nodes_to_use]
    # Dynamic penalty based on days remaining and demand

    data["penalties"] = [0] + get_penalty_list(demand_dict, BASE_PENALTY, TOTAL_DAYS)
    
    return data