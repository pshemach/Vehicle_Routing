"""
Solver module for the Vehicle Routing Problem.
Implements different solvers for the VRP.
"""

from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from vehi_rout.data_model.vrp_data_model import create_data_model
from vehi_rout.utils.helper_utils import get_penalty_list
import vehi_rout.config as config

def solve_vrp_for_day(
    full_matrix,
    nodes_to_visit,
    day,
    demand_dict,
    penalty_list=None,
    use_distance=True,
    geo_constraints=None,
    order_time_window=None,
    order_groups=None,
    priority_orders=None,
    vehicle_constraints=None
):
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

    matrix = data["distance_matrix"] if use_distance else data["time_matrix"]
    manager = pywrapcp.RoutingIndexManager(len(matrix), data["num_vehicles"], data["depot"])
    routing = pywrapcp.RoutingModel(manager)

    # --------- Step 1: Register vehicle-specific callbacks ---------
    transit_callback_indices = []

    def make_vehicle_cb(vehicle_id):
        def cb(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            cost = int(data["distance_matrix"][from_node][to_node])

            # Enforce geo constraints
            if geo_constraints and vehicle_constraints:
                from_code = str(data["node_mapping"][from_node])
                to_code = str(data["node_mapping"][to_node])
                veh_id = vehicle_constraints[vehicle_id]["vehicleId"]

                for gc in geo_constraints:
                    if gc["restrictedVehicle"] == veh_id:
                        # Match both directions
                        if {from_code, to_code} == {gc["fromCode"], gc["toCode"]}:
                            return 999999  # effectively prohibited

            return cost
        return cb

    for v in range(data["num_vehicles"]):
        idx = routing.RegisterTransitCallback(make_vehicle_cb(v))
        routing.SetArcCostEvaluatorOfVehicle(idx, v)
        transit_callback_indices.append(idx)

    # --------- Step 2: Distance/Time Dimension ---------
    dimension_name = "Distance" if use_distance else "Time"
    max_per_vehicle = data["max_distance_per_vehicle"] if use_distance else data["max_time_per_vehicle"]

    routing.AddDimensionWithVehicleTransits(
        transit_callback_indices,
        0,
        max(max_per_vehicle),
        True,
        dimension_name
    )

    dimension = routing.GetDimensionOrDie(dimension_name)
    for v in range(data["num_vehicles"]):
        dimension.CumulVar(routing.End(v)).SetMax(max_per_vehicle[v])

    # --------- Step 3: Visits Capacity ---------
    def demand_cb(from_index):
        return data["demands"][manager.IndexToNode(from_index)]

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx,
        0,
        data["max_visits_per_vehicle"],
        True,
        "Visits"
    )

    routing.SetFixedCostOfAllVehicles(10000)

    # --------- Step 4: Penalties for unvisited nodes ---------
    for node in range(1, len(matrix)):
        node_code = str(data["node_mapping"][node])
        idx = manager.NodeToIndex(node)
        
        if priority_orders and node_code in priority_orders.get("shopCodes", []):
            # Make it mandatory: don't add disjunction
            continue
        else:
            routing.AddDisjunction([idx], data["penalties"][node])

            

        # 🔹 Order Groups: force nodes into same vehicle
        if order_groups:
            for grp in order_groups:
                shop_codes = grp.get('shopCodes', [])
                group_indices = []

                for sc in shop_codes:
                    sc_str = str(sc)
                    if sc_str in data["node_mapping"]:
                        node_idx = data["node_mapping"].index(sc_str)
                        # Skip depot
                        if node_idx > 0:
                            group_indices.append(manager.NodeToIndex(node_idx))

                if len(group_indices) > 1:
                    # Force all nodes to be on the same vehicle
                    for i in range(1, len(group_indices)):
                        routing.solver().Add(
                            routing.VehicleVar(group_indices[0]) == routing.VehicleVar(group_indices[i])
                        )



    # --------- Step 6: Solve ---------
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = config.SOLVER_TIME_LIMIT_SECONDS

    solution = routing.SolveWithParameters(search_parameters)
    if solution:
        return print_solution(manager, routing, solution, data, day, use_distance)
    else:
        print(f"No solution found for Day {day+1}!")
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