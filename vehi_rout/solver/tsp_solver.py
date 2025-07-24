"""
Traveling Salesman Problem solver for pre-defined routes.
"""

from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import vehi_rout.config as config

def solve_tsp_for_route(matrix_df, shop_codes, demand_dict=None, use_distance=True, max_distance=None, max_visits=None):
    """
    Solve the Traveling Salesman Problem for a pre-defined route.

    Args:
        matrix_df: DataFrame containing the distance/time matrix
        shop_codes: List of shop codes in the pre-defined route
        demand_dict: Dictionary containing demand information
        use_distance: Boolean indicating whether to use distance or time
        max_distance: Maximum distance for the route
        max_visits: Maximum visits for the route

    Returns:
        route_nodes: List of node indices in the optimized route
        route_info: Dictionary containing route information
    """
    # Print input information for debugging
    print(f"TSP solver received {len(shop_codes)} shop codes")

    # Filter shop codes to only include those in the matrix
    valid_shop_codes = [code for code in shop_codes if code in matrix_df.index]
    invalid_codes = [code for code in shop_codes if code not in matrix_df.index]

    # Print filtering results
    if invalid_codes:
        print(f"Warning: {len(invalid_codes)} shop codes not found in distance matrix: {invalid_codes[:5]}{'...' if len(invalid_codes) > 5 else ''}")

    # If no valid shop codes, return empty route
    if not valid_shop_codes:
        print("No valid shop codes found in the distance matrix. Skipping route.")
        return [], {}

    # Add depot (0) to the beginning and end of the route
    depot_code = matrix_df.index[0]
    if depot_code not in valid_shop_codes:
        valid_shop_codes = [depot_code] + valid_shop_codes

    # Create distance matrix for the TSP
    tsp_matrix = []
    for i in valid_shop_codes:
        row = []
        for j in valid_shop_codes:
            if i in matrix_df.index and j in matrix_df.index:
                # Convert to float first, then to int to ensure we have numeric values
                distance_value = float(matrix_df.loc[i, j])
                row.append(distance_value)
            else:
                row.append(0)  # Default value if shop code not in matrix
        tsp_matrix.append(row)

    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(tsp_matrix), 1, 0)

    # Create Routing Model
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        try:
            # Ensure we're dealing with a numeric value
            value = float(tsp_matrix[from_node][to_node])
            return int(value)
        except (ValueError, TypeError):
            # If conversion fails, return a default value
            print(f"Warning: Could not convert distance value to int: {tsp_matrix[from_node][to_node]}")
            return 0

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Distance dimension
    dimension_name = 'Distance'
    # Use or operator instead of if-else for default value
    max_distance_value = max_distance or 3000

    # Ensure max_distance_value is an integer
    try:
        max_distance_value = int(float(max_distance_value))
    except (ValueError, TypeError):
        print(f"Warning: Could not convert max_distance to int: {max_distance}. Using default value 3000.")
        max_distance_value = 3000

    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        max_distance_value,  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name)

    # Get the dimension for potential future use
    distance_dimension = routing.GetDimensionOrDie(dimension_name)

    # Setting first solution heuristic
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = config.SOLVER_TIME_LIMIT_SECONDS

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        # Get the optimized route
        route_nodes = []
        index = routing.Start(0)
        route_distance = 0
        previous_index = index

        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_nodes.append(valid_shop_codes[node_index])
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)

        # Add the depot at the end
        node_index = manager.IndexToNode(index)
        route_nodes.append(valid_shop_codes[node_index])

        # Create route info dictionary
        metric_name = "distance" if use_distance else "time"

        # Ensure max_distance is an integer
        max_distance_value = max_distance or 3000
        try:
            max_distance_value = int(float(max_distance_value))
        except (ValueError, TypeError):
            max_distance_value = 3000

        # Ensure max_visits is an integer
        max_visits_value = max_visits or len(route_nodes)
        try:
            max_visits_value = int(float(max_visits_value))
        except (ValueError, TypeError):
            max_visits_value = len(route_nodes)

        route_info = {
            "route_nodes": route_nodes,
            f"route_{metric_name}": route_distance,
            f"max_{metric_name}_limit": max_distance_value,
            "within_limit": route_distance <= max_distance_value,
            "num_visits": len(route_nodes) - 2,  # Subtract depot at start and end
            "max_visits_limit": max_visits_value
        }

        # Print summary of the optimized route
        print(f"TSP solution found: {len(route_nodes)} stops, {route_distance} {metric_name} units")
        print(f"Route: {route_nodes[0]} -> ... -> {route_nodes[-1]}")

        return route_nodes, route_info
    else:
        print("No solution found for TSP!")
        return [], {}
