from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from data_model.vrp_data_model import create_data_model
from router.vrp_duration_printer import print_solution

def solve_vrp_for_day(full_matrix, nodes_to_visit, day, demand_dict):
    data = create_data_model(full_matrix, nodes_to_visit, demand_dict)
    manager = pywrapcp.RoutingIndexManager(len(data["time_matrix"]), data["num_vehicles"], data["depot"])
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        time = int(data["time_matrix"][from_node][to_node])
        return time

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Time dimension
    routing.AddDimension(
        transit_callback_index,
        0,
        max(data["max_time_per_vehicle"]),
        True,
        "Time"
    )
    time_dimension = routing.GetDimensionOrDie("Time")
    for vehicle_id in range(data["num_vehicles"]):
        end_index = routing.End(vehicle_id)
        time_dimension.CumulVar(end_index).SetMax(data["max_time_per_vehicle"][vehicle_id])

    # Demand dimension
    def demand_callback(from_index):
        return data["demands"][manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        data["max_visits_per_vehicle"],
        True,
        "Visits"
    )

    # Optional nodes with demand-based penalty
    for node in range(1, len(data["time_matrix"])):
        routing.AddDisjunction([manager.NodeToIndex(node)], data["penalties"][node])

    # Search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = 30

    solution = routing.SolveWithParameters(search_parameters)
    if solution:
        return print_solution(manager, routing, solution, data, day)
    else:
        print(f"No solution found for Day {day + 1}!")
        return set()