def print_solution(manager, routing, solution, data, day):
    total_time = 0
    visited_nodes = set()
    print(f"\nDay {day + 1} Routes (Penalty per unvisited demand unit: {data['penalties'][1]} mins):")
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        plan_output = f"Route for vehicle {vehicle_id}:\n"
        route_time = 0
        num_visits = 0
        previous_node = None
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            original_node = data["node_mapping"][node]
            visited_nodes.add(original_node)
            plan_output += f" {original_node} ->"
            if previous_node is not None:
                arc_time = int(data["time_matrix"][previous_node][node])
                route_time += arc_time
            previous_node = node
            index = solution.Value(routing.NextVar(index))
            if original_node != data["depot"]:
                num_visits += 1
        node = manager.IndexToNode(index)
        original_node = data["node_mapping"][node]
        visited_nodes.add(original_node)
        plan_output += f" {original_node}\n"
        if previous_node is not None:
            arc_time = int(data["time_matrix"][previous_node][node])
            route_time += arc_time
        plan_output += f"Time of the route: {route_time} mins\n"
        max_time = data["max_time_per_vehicle"][vehicle_id]
        plan_output += f"Within limit: {'Yes' if route_time <= max_time else 'No'} (Max: {max_time} mins)\n"
        plan_output += f"Stops visited: {num_visits}/{data['max_visits_per_vehicle'][vehicle_id]}\n"
        print(plan_output)
        total_time = max(total_time, route_time)
    print(f"Maximum route time for Day {day + 1}: {total_time} mins")
    return visited_nodes