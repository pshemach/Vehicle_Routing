"""
Solver module for the Vehicle Routing Problem.
Implements different solvers for the VRP.
"""

from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from vehi_rout.data_model.vrp_data_model import create_data_model
from vehi_rout.utils.helper_utils import get_penalty_list
import vehi_rout.config as config

# def solve_vrp_for_day(full_matrix, nodes_to_visit, day, demand_dict, penalty_list=None, use_distance=True):
#     """
#     Solve the Vehicle Routing Problem for a single day.

#     Args:
#         full_matrix: DataFrame containing the distance/time matrix
#         nodes_to_visit: List of node indices to visit
#         day: Day index (0-based)
#         demand_dict: Dictionary containing demand information
#         penalty_list: List of penalties for not visiting nodes
#         use_distance: Boolean indicating whether to use distance or time

#     Returns:
#         visited_nodes: Set of visited node indices
#         route_dict: Dictionary containing route information for each vehicle
#     """
#     # Create data model
#     data = create_data_model(full_matrix, nodes_to_visit, demand_dict, penalty_list, use_distance)

#     # Create routing index manager
#     manager = pywrapcp.RoutingIndexManager(
#         len(data["distance_matrix" if use_distance else "time_matrix"]),
#         data["num_vehicles"],
#         data["depot"]
#     )

#     # Create routing model
#     routing = pywrapcp.RoutingModel(manager)

#     # Create and register transit callback
#     def transit_callback(from_index, to_index):
#         from_node = manager.IndexToNode(from_index)
#         to_node = manager.IndexToNode(to_index)
#         return int(data["distance_matrix" if use_distance else "time_matrix"][from_node][to_node])

#     transit_callback_index = routing.RegisterTransitCallback(transit_callback)
#     routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

#     # Add distance/time dimension
#     dimension_name = "Distance" if use_distance else "Time"
#     max_per_vehicle = data["max_distance_per_vehicle" if use_distance else "max_time_per_vehicle"]

#     routing.AddDimension(
#         transit_callback_index,
#         0,  # no slack
#         max(max_per_vehicle),  # maximum distance/time
#         True,  # start cumul to zero
#         dimension_name
#     )

#     dimension = routing.GetDimensionOrDie(dimension_name)

#     # Set individual vehicle limits
#     for vehicle_id in range(data["num_vehicles"]):
#         end_index = routing.End(vehicle_id)
#         dimension.CumulVar(end_index).SetMax(max_per_vehicle[vehicle_id])

#     # Add capacity dimension
#     def demand_callback(from_index):
#         from_node = manager.IndexToNode(from_index)
#         return data["demands"][from_node]

#     demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

#     routing.AddDimensionWithVehicleCapacity(
#         demand_callback_index,
#         0,  # null capacity slack
#         data["max_visits_per_vehicle"],  # vehicle maximum capacities
#         True,  # start cumul to zero
#         "Visits"
#     )

#     # Add penalties for skipping nodes
#     for node in range(1, len(data["distance_matrix" if use_distance else "time_matrix"])):
#         routing.AddDisjunction([manager.NodeToIndex(node)], data["penalties"][node])

#     # Set search parameters
#     search_parameters = pywrapcp.DefaultRoutingSearchParameters()
#     search_parameters.first_solution_strategy = (
#         routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
#     )
#     search_parameters.local_search_metaheuristic = (
#         routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
#     )
#     search_parameters.time_limit.seconds = SOLVER_TIME_LIMIT_SECONDS

#     # Solve the problem
#     solution = routing.SolveWithParameters(search_parameters)

#     if solution:
#         return print_solution(manager, routing, solution, data, day, use_distance)
#     else:
#         print(f"No solution found for Day {day + 1}!")
#         return set(), {}

def solve_vrp_for_day(full_matrix, nodes_to_visit, day, demand_dict, penalty_list=None, use_distance=True):
    """
    Solve the Vehicle Routing Problem for a single day.

    Args:
        full_matrix: DataFrame containing the distance/time matrix
        nodes_to_visit: List of node indices to visit
        day: Day index (0-based)
        demand_dict: Dictionary containing demand information
        penalty_list: List of penalties for not visiting nodes
        use_distance: Boolean indicating whether to use distance or time

    Returns:
        visited_nodes: Set of visited node indices
        route_dict: Dictionary containing route information for each vehicle
    """

    # Step 1: Create data model using current config values
    data = create_data_model(
        full_matrix=full_matrix,
        nodes_to_visit=nodes_to_visit,
        demand_dict=demand_dict,
        penalty_list=penalty_list,
        use_distance=use_distance,
        max_distance=config.MAX_DISTANCE_PER_VEHICLE,
        max_time=config.MAX_TIME_PER_VEHICLE,
        max_visits=config.MAX_VISITS_PER_VEHICLE
    )

    print("Max Distance:", data["max_distance_per_vehicle"])

    # Step 2: Set up OR-Tools manager and model
    matrix = data["distance_matrix"] if use_distance else data["time_matrix"]
    manager = pywrapcp.RoutingIndexManager(len(matrix), data["num_vehicles"], data["depot"])
    routing = pywrapcp.RoutingModel(manager)

    # Step 3: Register transit callback
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(data["distance_matrix"][from_node][to_node])

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Step 4: Add Distance/Time dimension
    dimension_name = "Distance" if use_distance else "Time"
    max_per_vehicle = data["max_distance_per_vehicle"] if use_distance else data["max_time_per_vehicle"]

    routing.AddDimension(
        transit_callback_index,
        0,  # slack
        max(max_per_vehicle),  # global max limit
        True,  # start cumul to zero
        dimension_name
    )

    dimension = routing.GetDimensionOrDie(dimension_name)
    for vehicle_id in range(data["num_vehicles"]):
        end_index = routing.End(vehicle_id)
        dimension.CumulVar(end_index).SetMax(max_per_vehicle[vehicle_id])

    # Step 5: Add demand/capacity dimension
    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data["demands"][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        data["max_visits_per_vehicle"],
        True,
        "Visits"
    )

    routing.SetFixedCostOfAllVehicles(10000)

    # Step 6: Add penalties for not visiting nodes
    for node in range(1, len(matrix)):
        routing.AddDisjunction([manager.NodeToIndex(node)], data["penalties"][node])

    # Step 7: Set search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = config.SOLVER_TIME_LIMIT_SECONDS

    # Step 8: Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        return print_solution(manager, routing, solution, data, day, use_distance)
    else:
        print(f"No solution found for Day {day + 1}!")
        return set(), {}

def print_solution(manager, routing, solution, data, day, use_distance=False):
    """
    Print the solution and return visited nodes and route information.

    Args:
        manager: OR-Tools routing index manager
        routing: OR-Tools routing model
        solution: OR-Tools solution
        data: Data model
        day: Day index (0-based)
        use_distance: Boolean indicating whether to use distance or time

    Returns:
        visited_nodes: Set of visited node indices
        route_dict: Dictionary containing route information for each vehicle
    """
    total_metric = 0  # Total distance or time
    visited_nodes = set()
    route_dict = {}  # Dictionary to store route details for each vehicle

    metric_name = "distance" if use_distance else "time"
    max_metric_name = f"max_{metric_name}_per_vehicle"
    unit = "km" if use_distance else "mins"

    print(f"\nDay {day + 1} Routes (Penalty per unvisited demand unit: {data['penalties'][1]} {unit}):")

    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        plan_output = f"Route for vehicle {vehicle_id}:\n"
        route_metric = 0
        num_visits = 0
        route_nodes = []
        previous_node = None

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            original_node = data["node_mapping"][node]
            visited_nodes.add(original_node)
            route_nodes.append(original_node)

            plan_output += f" {original_node} ->"

            if previous_node is not None:
                arc_metric = int(data[f"{metric_name}_matrix"][previous_node][node])
                route_metric += arc_metric

            previous_node = node
            index = solution.Value(routing.NextVar(index))

            if original_node != data["depot"]:
                num_visits += 1

        # Handle the return to depot
        node = manager.IndexToNode(index)
        original_node = data["node_mapping"][node]
        visited_nodes.add(original_node)
        route_nodes.append(original_node)

        plan_output += f" {original_node}\n"

        if previous_node is not None:
            arc_metric = int(data[f"{metric_name}_matrix"][previous_node][node])
            route_metric += arc_metric

        plan_output += f"{metric_name.capitalize()} of the route: {route_metric} {unit}\n"
        max_metric = data[max_metric_name][vehicle_id]
        plan_output += f"Within limit: {'Yes' if route_metric <= max_metric else 'No'} (Max: {max_metric} {unit})\n"
        plan_output += f"Stops visited: {num_visits-1}/{data['max_visits_per_vehicle'][vehicle_id]}\n"

        # Store route details in the dictionary
        route_dict[vehicle_id] = {
            "route_nodes": route_nodes,
            f"route_{metric_name}": route_metric,
            f"max_{metric_name}_limit": max_metric,
            "within_limit": route_metric <= max_metric,
            "num_visits": num_visits-1,
            "max_visits_limit": data["max_visits_per_vehicle"][vehicle_id]
        }

        print(plan_output)
        total_metric = max(total_metric, route_metric)

    print(f"Maximum route {metric_name} for Day {day + 1}: {total_metric} {unit}")

    return visited_nodes, route_dict

def solve_multi_day_vrp(full_matrix, demand_dict, total_days, base_penalty, use_distance=True, current_date=None, max_nodes_per_day=None):
    """
    Solve the Vehicle Routing Problem for multiple days.

    Args:
        full_matrix: DataFrame containing the distance/time matrix
        demand_dict: Dictionary containing demand information
        total_days: Number of days to plan
        base_penalty: Base penalty for not visiting nodes
        use_distance: Boolean indicating whether to use distance or time
        current_date: Current date in format 'YYYY-MM-DD'
        max_nodes_per_day: Maximum number of nodes to visit per day

    Returns:
        all_visited_nodes: List of sets of visited node indices for each day
        all_route_dicts: List of dictionaries containing route information for each day
    """
    from vehi_rout.utils.helper_utils import get_values_not_in_second_list
    from vehi_rout.utils.route_utils import sort_nodes_by_distance

    all_visited_nodes = []
    all_route_dicts = []

    # Sort nodes by distance from depot
    sorted_nodes = sort_nodes_by_distance(full_matrix.values)

    # Limit the number of nodes if specified
    if max_nodes_per_day is not None and max_nodes_per_day < len(sorted_nodes):
        nodes_to_consider = sorted(sorted_nodes[:max_nodes_per_day])
    else:
        nodes_to_consider = list(range(1, len(full_matrix)))

    remaining_nodes = nodes_to_consider

    for day in range(total_days):
        # Calculate penalties based on days remaining
        penalty_list = get_penalty_list(demand_dict, base_penalty, total_days, current_date)

        # Solve VRP for current day
        visited_nodes, route_dict = solve_vrp_for_day(
            full_matrix,
            remaining_nodes,
            day,
            demand_dict,
            penalty_list,
            use_distance
        )

        all_visited_nodes.append(visited_nodes)
        all_route_dicts.append(route_dict)

        # Update remaining nodes
        remaining_nodes = get_values_not_in_second_list(remaining_nodes, visited_nodes)

        # If all nodes have been visited, we can stop
        if not remaining_nodes:
            break

    return all_visited_nodes, all_route_dicts
