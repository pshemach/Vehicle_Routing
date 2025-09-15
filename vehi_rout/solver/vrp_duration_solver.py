from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import vehi_rout.config as config
from vehi_rout.data_model.vrp_data_model import create_data_model
from datetime import datetime, timedelta


def solve_vrp_time(
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
    # ⏳ Parse max route duration from vehicle_constraints
    max_time = []
    if vehicle_constraints:
        for v in vehicle_constraints:
            start, end = v['timeWindow'].split('-')
            t1 = datetime.strptime(start, "%H:%M")
            t2 = datetime.strptime(end, "%H:%M")
            max_time.append(int((t2 - t1).total_seconds() / 60))  # minutes

    # 1️⃣ Create data model
    data = create_data_model(
        full_matrix=full_matrix,
        nodes_to_visit=nodes_to_visit,
        demand_dict=demand_dict,
        penalty_list=penalty_list,
        use_distance=use_distance,
        max_distance=config.MAX_DISTANCE_PER_VEHICLE,
        max_time=max_time,
        max_visits=config.MAX_VISITS_PER_VEHICLE
    )

    matrix = data["distance_matrix"] if use_distance else data["time_matrix"]
    manager = pywrapcp.RoutingIndexManager(len(matrix), data["num_vehicles"], data["depot"])
    routing = pywrapcp.RoutingModel(manager)

    # 2️⃣ Vehicle-specific transit cost (with geo constraints)
    def make_vehicle_cb(vehicle_id):
        def cb(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            cost = int(matrix[from_node][to_node])
            if geo_constraints and vehicle_constraints:
                from_code = str(full_matrix.index[from_node])
                to_code = str(full_matrix.index[to_node])
                veh_id = vehicle_constraints[vehicle_id]["vehicleId"]
                for gc in geo_constraints:
                    if gc["restrictedVehicle"] == veh_id and {from_code, to_code} == {gc["fromCode"], gc["toCode"]}:
                        return 999999  # prohibit
            return cost
        return cb

    transit_callback_indices = []
    for v in range(data["num_vehicles"]):
        cb_index = routing.RegisterTransitCallback(make_vehicle_cb(v))
        routing.SetArcCostEvaluatorOfVehicle(cb_index, v)
        transit_callback_indices.append(cb_index)

    # 3️⃣ Travel Distance/Time dimension
    dim_name = "Distance" if use_distance else "Time"
    max_per_vehicle = data["max_distance_per_vehicle"] if use_distance else data["max_time_per_vehicle"]

    routing.AddDimensionWithVehicleTransits(
        transit_callback_indices,
        0, max(max_per_vehicle),
        True, dim_name
    )
    dist_dim = routing.GetDimensionOrDie(dim_name)
    for v in range(data["num_vehicles"]):
        dist_dim.CumulVar(routing.End(v)).SetMax(max_per_vehicle[v])

    # 4️⃣ Capacity dimension (visits)
    def demand_cb(from_index):
        return data["demands"][manager.IndexToNode(from_index)]
    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx, 0, data["max_visits_per_vehicle"],
        True, "Visits"
    )

    routing.SetFixedCostOfAllVehicles(10000)

    # 5️⃣ Time Window dimension (if enabled)
    if order_time_window:
        def time_cb(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            travel = matrix[from_node][to_node]
            service = data["service_times"][from_node]
            return int(travel + service)
        time_cb_idx = routing.RegisterTransitCallback(time_cb)

        routing.AddDimension(
            time_cb_idx,
            30_000,
            max(data["max_time_per_vehicle"]),
            False,
            "Time"
        )
        time_dim = routing.GetDimensionOrDie("Time")

        # Apply order time windows
        for node_idx, shop_code in enumerate(data["node_mapping"]):
            if str(shop_code) in order_time_window:
                start, end = order_time_window[str(shop_code)]
                routing_idx = manager.NodeToIndex(node_idx)
                time_dim.CumulVar(routing_idx).SetRange(start, end)

        # Depot window
        depot_start, depot_end = order_time_window.get("0", (0, 10000))
        for v in range(data["num_vehicles"]):
            time_dim.CumulVar(routing.Start(v)).SetRange(depot_start, depot_end)
            time_dim.CumulVar(routing.End(v)).SetRange(depot_start, depot_end)

        time_dim.SetGlobalSpanCostCoefficient(100)

    # 6️⃣ Add disjunctions and penalties
    high_penalty = 100000
    for node in range(1, len(matrix)):
        code = str(full_matrix.index[node])
        penalty = high_penalty if priority_orders and code in priority_orders.get("shopCodes", []) else data["penalties"][node]
        routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    # 7️⃣ Order Groups
    if order_groups:
        for group in order_groups:
            codes = group.get('shopCodes', [])
            indices = [manager.NodeToIndex(data["node_mapping"].index(sc)) for sc in codes if sc in data["node_mapping"]]
            if len(indices) > 1:
                for i in range(len(indices)-1):
                    routing.AddPickupAndDelivery(indices[i], indices[i+1])
                    routing.solver().Add(routing.VehicleVar(indices[i]) == routing.VehicleVar(indices[i+1]))

    # 🔟 Solver configuration
    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_params.time_limit.seconds = config.SOLVER_TIME_LIMIT_SECONDS

    solution = routing.SolveWithParameters(search_params)
    if solution:
        return print_solution(manager, routing, solution, data, day, use_distance)
    else:
        print(f"❌ No solution found for Day {day+1}")
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
