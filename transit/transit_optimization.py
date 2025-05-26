import json
import networkx as nx
import itertools

# --- Data Loading (Shared logic - consider a common utility) ---
def load_json_data(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Data file not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None

def get_transit_data(transit_data_path):
    """Loads all transit-related data (metro, bus, demand)."""
    return load_json_data(transit_data_path)

def get_base_road_network_for_transit(road_data_path, facilities_data_path):
    """Loads the road network graph, which transit routes might overlay or connect to."""
    road_data = load_json_data(road_data_path)
    facilities_data = load_json_data(facilities_data_path)
    if not road_data:
        return None
    graph = nx.Graph() # Use Graph as base, specific transit routes are sequences on this
    if "nodes" in road_data:
        for node_info in road_data["nodes"]:
            graph.add_node(str(node_info["ID"]), **node_info)
    if facilities_data:
        for facility_info in facilities_data:
            fid = str(facility_info["ID"])
            if fid not in graph: graph.add_node(fid, **facility_info)
            else: graph.nodes[fid].update(facility_info)
    # Edges might not be directly used for high-level transit opt, but good for context
    if "edges" in road_data:
        for edge_info in road_data["edges"]:
            u, v = str(edge_info["FromID"]), str(edge_info["ToID"])
            if graph.has_node(u) and graph.has_node(v):
                 graph.add_edge(u,v, **edge_info)
    return graph

# --- Transit Optimization Algorithms (Conceptual) ---

# 1. Optimize Bus Allocation based on Demand (Greedy Approach)
def optimize_bus_allocation_greedy(bus_routes_data, demand_data, total_buses_available):
    """
    Allocates buses to routes greedily based on passenger demand per bus.
    This is a simplified model. Real optimization is far more complex.
    Args:
        bus_routes_data (list): List of bus routes with current buses and passengers.
        demand_data (list): List of O-D passenger demand pairs.
        total_buses_available (int): Total fleet size.
    Returns:
        dict: Optimized bus allocations per route.
    """
    if not bus_routes_data:
        return {"error": "No bus routes data provided."}

    # Calculate demand covered by each existing route (simplified)
    route_demands = {route["RouteID"]: 0 for route in bus_routes_data}
    for route in bus_routes_data:
        # Simplified: sum demand if route covers O or D. Better: check if route serves O-D pair.
        # This is a very rough estimation of demand relevance.
        route_stops = set(route.get("Stops_comma_separated_IDs", []))
        for dem_pair in demand_data:
            if dem_pair["FromID"] in route_stops and dem_pair["ToID"] in route_stops:
                route_demands[route["RouteID"]] += dem_pair["Daily_Passengers"]
            elif dem_pair["FromID"] in route_stops or dem_pair["ToID"] in route_stops:
                 route_demands[route["RouteID"]] += dem_pair["Daily_Passengers"] * 0.5 # Partial coverage

    # Calculate a "priority score" for each route (e.g., demand / current buses, or just demand)
    route_priority = []
    for route in bus_routes_data:
        demand = route_demands.get(route["RouteID"], route.get("Daily_Passengers", 0)) # Use provided passengers if demand calc is poor
        # Score: higher demand = higher priority. If buses assigned, can use demand/bus.
        # For initial allocation, just use demand.
        score = demand
        route_priority.append({"RouteID": route["RouteID"], "score": score, "current_buses": route.get("Buses_Assigned",0)})
    
    route_priority.sort(key=lambda x: x["score"], reverse=True)

    # Allocate buses greedily based on score
    # This is a proportional allocation based on score
    total_score = sum(r["score"] for r in route_priority)
    if total_score == 0: # Avoid division by zero if no demand/score
        # Fallback: distribute evenly or based on current if total_buses matches sum of current
        current_total_buses = sum(r["current_buses"] for r in route_priority)
        if total_buses_available == current_total_buses:
            return {r["RouteID"]: r["current_buses"] for r in route_priority}
        else: # Distribute somewhat evenly if no other info
            buses_per_route = total_buses_available // len(route_priority) if len(route_priority) > 0 else 0
            remainder = total_buses_available % len(route_priority) if len(route_priority) > 0 else 0
            optimized_allocation = {r["RouteID"]: buses_per_route for r in route_priority}
            for i in range(remainder):
                optimized_allocation[route_priority[i]["RouteID"]] +=1
            return optimized_allocation

    optimized_allocation = {}
    allocated_buses_sum = 0
    for route_info in route_priority:
        proportion = route_info["score"] / total_score if total_score > 0 else 0
        num_buses = round(proportion * total_buses_available)
        optimized_allocation[route_info["RouteID"]] = int(num_buses)
        allocated_buses_sum += int(num_buses)
    
    # Adjust if rounding caused over/under allocation
    diff = total_buses_available - allocated_buses_sum
    idx = 0
    while diff != 0:
        route_id_to_adjust = route_priority[idx % len(route_priority)]["RouteID"]
        if diff > 0:
            optimized_allocation[route_id_to_adjust] += 1
            diff -= 1
        elif diff < 0 and optimized_allocation[route_id_to_adjust] > 0:
            optimized_allocation[route_id_to_adjust] -= 1
            diff += 1
        elif diff < 0 and optimized_allocation[route_id_to_adjust] == 0:
            pass # Cannot reduce further
        idx += 1
        if idx > len(route_priority) * 2 and diff !=0 : # Safety break for difficult adjustments
            print(f"Warning: Could not perfectly allocate buses. Diff: {diff}")
            break
            
    return optimized_allocation

# 2. Metro Line Extension/New Route Feasibility (Conceptual - based on demand coverage)
# This would typically involve complex modeling. Here, a very simplified score.
def assess_new_metro_line_feasibility(potential_line_stations, demand_data, existing_metro_lines, road_network):
    """
    Conceptually assesses feasibility of a new metro line based on uncovered demand.
    Args:
        potential_line_stations (list): List of station IDs for the new potential line.
        demand_data (list): O-D passenger demand.
        existing_metro_lines (list): Data for existing metro lines.
        road_network (nx.Graph): Base road network for context (e.g. connectivity).
    Returns:
        dict: Feasibility score and rationale.
    """
    uncovered_demand_score = 0
    covered_by_new_line = 0
    total_demand_points = len(demand_data)

    # Identify stations already well-served by existing metro
    well_served_stations = set()
    for line in existing_metro_lines:
        for station in line.get("Stations_comma_separated_IDs", []):
            well_served_stations.add(station)

    potential_line_set = set(potential_line_stations)

    for demand_pair in demand_data:
        from_node, to_node = demand_pair["FromID"], demand_pair["ToID"]
        passengers = demand_pair["Daily_Passengers"]

        # Check if this demand is met by the new line
        serves_from = from_node in potential_line_set
        serves_to = to_node in potential_line_set
        
        if serves_from and serves_to:
            covered_by_new_line += passengers
            # If these stations are NOT currently well-served, it adds more to score
            if from_node not in well_served_stations or to_node not in well_served_stations:
                uncovered_demand_score += passengers * 1.0
            else: # Still useful, but less critical if already served
                uncovered_demand_score += passengers * 0.3 
        elif serves_from or serves_to: # Partial coverage (e.g. feeder)
            covered_by_new_line += passengers * 0.5
            if ((serves_from and from_node not in well_served_stations) or 
                (serves_to and to_node not in well_served_stations)):
                uncovered_demand_score += passengers * 0.4
            else:
                uncovered_demand_score += passengers * 0.1

    # Connectivity score: does the new line connect to existing lines or important hubs?
    connectivity_score = 0
    for station in potential_line_stations:
        if station in well_served_stations: # Connects to existing metro
            connectivity_score += 5000 # Arbitrary bonus
        if road_network and station in road_network and road_network.nodes[station].get("Type") in ["Transit Hub", "Airport", "Major Facility"]:
            connectivity_score += road_network.nodes[station].get("Population", 10000) # Bonus for connecting to hubs

    final_score = uncovered_demand_score + connectivity_score
    return {
        "potential_line": potential_line_stations,
        "estimated_passengers_served_direct_or_partial": round(covered_by_new_line),
        "uncovered_demand_score_component": round(uncovered_demand_score),
        "connectivity_score_component": round(connectivity_score),
        "total_feasibility_score": round(final_score)
    }

if __name__ == "__main__":
    print("Testing Transit Optimization Functions")
    base_data_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    transit_data_file = base_data_path + r"\transit_data.json"
    road_data_file = base_data_path + r"\road_data.json"
    facilities_data_file = base_data_path + r"\facilities.json"

    transit_data_content = get_transit_data(transit_data_file)
    road_net = get_base_road_network_for_transit(road_data_file, facilities_data_file)

    if transit_data_content and road_net:
        bus_routes = transit_data_content.get("bus_routes", [])
        metro_lines = transit_data_content.get("metro_lines", [])
        pt_demand = transit_data_content.get("public_transport_demand", [])
        
        # Test 1: Optimize Bus Allocation
        total_buses_in_fleet = sum(r.get("Buses_Assigned",0) for r in bus_routes) + 10 # Example: current fleet + 10 more
        print(f"\n--- Optimizing Bus Allocation (Total Fleet: {total_buses_in_fleet}) ---")
        if bus_routes and pt_demand:
            optimized_buses = optimize_bus_allocation_greedy(bus_routes, pt_demand, total_buses_in_fleet)
            if "error" not in optimized_buses:
                print("Optimized Bus Allocations:")
                for route_id, num_buses in optimized_buses.items():
                    original_buses = next((r.get("Buses_Assigned",0) for r in bus_routes if r["RouteID"] == route_id), "N/A")
                    print(f"  Route {route_id}: {num_buses} buses (Original: {original_buses})")
                print(f"Total buses allocated: {sum(optimized_buses.values())}")
            else:
                print(f"Error in bus allocation: {optimized_buses["error"]}")
        else:
            print("Skipping bus allocation test: Missing bus routes or demand data.")

        # Test 2: Assess New Metro Line Feasibility
        print("\n--- Assessing New Metro Line Feasibility ---")
        # Define a hypothetical new metro line (station IDs)
        # Example: A new line connecting some residential areas to business hubs or underserved areas
        # These IDs should exist in your road_data.json (as neighborhoods) or facilities.json
        potential_line_1 = ["1", "6", "14", "F3"] # Maadi, Heliopolis, New Cairo node, 6th October City Facility
        potential_line_2 = ["7", "15", "F5", "13"] # Zamalek, Garden City, Smart Village Facility, Sheikh Zayed node
        
        if pt_demand and metro_lines:
            assessment1 = assess_new_metro_line_feasibility(potential_line_1, pt_demand, metro_lines, road_net)
            print(f"Assessment for Potential Line 1 ({potential_line_1}):")
            for key, val in assessment1.items():
                print(f"  {key.replace("_", " ").title()}: {val}")

            assessment2 = assess_new_metro_line_feasibility(potential_line_2, pt_demand, metro_lines, road_net)
            print(f"\nAssessment for Potential Line 2 ({potential_line_2}):")
            for key, val in assessment2.items():
                print(f"  {key.replace("_", " ").title()}: {val}")
        else:
            print("Skipping metro feasibility test: Missing demand or existing metro lines data.")
    else:
        print("Failed to load transit data or road network for optimization testing.")

