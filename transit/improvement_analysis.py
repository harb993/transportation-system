import json
import statistics

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

# --- Transit Improvement Analysis Functions ---

def analyze_demand_coverage(transit_data, optimized_bus_allocations=None):
    """
    Analyzes how well existing/optimized transit services cover public transport demand.
    Args:
        transit_data (dict): Parsed from transit_data.json (contains metro, bus, demand).
        optimized_bus_allocations (dict, optional): Output from bus optimization, if available.
                                                  Maps RouteID to number of buses.
    Returns:
        dict: Analysis of demand coverage.
    """
    if not transit_data or "public_transport_demand" not in transit_data:
        return {"error": "Public transport demand data is missing."}

    demand_pairs = transit_data["public_transport_demand"]
    metro_lines = transit_data.get("metro_lines", [])
    bus_routes = transit_data.get("bus_routes", [])

    total_demand_passengers = sum(dp["Daily_Passengers"] for dp in demand_pairs)
    covered_passengers_direct_metro = 0
    covered_passengers_direct_bus = 0
    covered_passengers_any_direct = 0
    uncovered_demand_details = []

    # Build sets of stations/stops for quick lookup
    metro_station_sets = {}
    for line in metro_lines:
        metro_station_sets[line["LineID"]] = set(line.get("Stations_comma_separated_IDs", []))
    
    bus_stop_sets = {}
    for route in bus_routes:
        bus_stop_sets[route["RouteID"]] = set(route.get("Stops_comma_separated_IDs", []))

    for demand in demand_pairs:
        from_id, to_id = demand["FromID"], demand["ToID"]
        passengers = demand["Daily_Passengers"]
        is_covered_by_metro = False
        is_covered_by_bus = False

        # Check Metro Coverage (direct line)
        for line_id, stations in metro_station_sets.items():
            if from_id in stations and to_id in stations:
                is_covered_by_metro = True
                break
        
        if is_covered_by_metro:
            covered_passengers_direct_metro += passengers

        # Check Bus Coverage (direct route)
        # Consider optimized bus allocation if provided - a route with 0 buses doesn_t offer service
        for route_id, stops in bus_stop_sets.items():
            num_buses_on_route = (optimized_bus_allocations.get(route_id) if optimized_bus_allocations 
                                else next((r.get("Buses_Assigned",0) for r in bus_routes if r["RouteID"] == route_id), 0))
            if num_buses_on_route > 0 and from_id in stops and to_id in stops:
                is_covered_by_bus = True
                break
        
        if is_covered_by_bus:
            covered_passengers_direct_bus += passengers # This might double count if also metro covered

        if is_covered_by_metro or is_covered_by_bus:
            covered_passengers_any_direct += passengers
        else:
            uncovered_demand_details.append(demand)

    # More sophisticated: consider transfers, but that requires pathfinding on combined transit graph.
    # For now, this is direct coverage.

    percent_metro_direct = (covered_passengers_direct_metro / total_demand_passengers * 100) if total_demand_passengers > 0 else 0
    percent_bus_direct = (covered_passengers_direct_bus / total_demand_passengers * 100) if total_demand_passengers > 0 else 0
    percent_any_direct = (covered_passengers_any_direct / total_demand_passengers * 100) if total_demand_passengers > 0 else 0
    
    # Identify top N uncovered demand pairs
    top_uncovered = sorted(uncovered_demand_details, key=lambda x: x["Daily_Passengers"], reverse=True)[:10]

    return {
        "total_daily_demand_passengers": total_demand_passengers,
        "passengers_directly_covered_by_metro": covered_passengers_direct_metro,
        "passengers_directly_covered_by_bus": covered_passengers_direct_bus,
        "passengers_directly_covered_by_any_service": covered_passengers_any_direct,
        "percentage_metro_direct_coverage": round(percent_metro_direct, 2),
        "percentage_bus_direct_coverage": round(percent_bus_direct, 2),
        "percentage_any_direct_coverage": round(percent_any_direct, 2),
        "number_of_uncovered_od_pairs": len(uncovered_demand_details),
        "total_passengers_in_uncovered_od_pairs": sum(d["Daily_Passengers"] for d in uncovered_demand_details),
        "top_10_uncovered_demand_pairs": top_uncovered
    }

def suggest_route_extensions_or_new_routes(demand_coverage_analysis, transit_data, road_network_graph):
    """
    Suggests potential new routes or extensions based on uncovered demand.
    This is highly conceptual and would need geographic analysis / detailed pathfinding.
    Args:
        demand_coverage_analysis (dict): Output from analyze_demand_coverage.
        transit_data (dict): Full transit data.
        road_network_graph (nx.Graph): For context of node locations/connectivity.
    Returns:
        list: List of suggestions.
    """
    suggestions = []
    top_uncovered = demand_coverage_analysis.get("top_10_uncovered_demand_pairs", [])
    if not top_uncovered:
        return ["No significant uncovered demand identified for new route suggestions based on top 10."]

    existing_metro_stations = set()
    for line in transit_data.get("metro_lines", []):
        existing_metro_stations.update(line.get("Stations_comma_separated_IDs", []))
    
    existing_bus_stops = set()
    for route in transit_data.get("bus_routes", []):
        existing_bus_stops.update(route.get("Stops_comma_separated_IDs", []))

    for i, demand_pair in enumerate(top_uncovered):
        from_node, to_node = demand_pair["FromID"], demand_pair["ToID"]
        passengers = demand_pair["Daily_Passengers"]
        suggestion = f"High uncovered demand ({passengers} passengers/day) between {from_node} and {to_node}. "
        
        # Check if endpoints are near existing transit, suggesting extension
        from_near_metro = from_node in existing_metro_stations
        to_near_metro = to_node in existing_metro_stations
        from_near_bus = from_node in existing_bus_stops
        to_near_bus = to_node in existing_bus_stops

        if (from_near_metro and not to_near_metro) or (not from_near_metro and to_near_metro):
            suggestion += "Consider extending an existing Metro line or a feeder bus service. "
        elif (from_near_bus and not to_near_bus) or (not from_near_bus and to_near_bus):
            suggestion += "Consider extending an existing Bus route or creating a new connecting bus service. "
        elif not from_near_metro and not to_near_metro and not from_near_bus and not to_near_bus:
            suggestion += "This O-D pair seems underserved. A new direct Bus route or a new Metro segment could be evaluated. "
        else: # Both might be near different lines/routes, or same but not direct
            suggestion += "Investigate direct bus route or better transfer options. "
        
        # Conceptual: Check for intermediate high-demand points if road_network_graph is available
        # This would require pathfinding and checking demand along potential paths.
        # For now, this is a high-level suggestion.
        suggestions.append(suggestion)
        if i >= 4: # Limit to top 5 suggestions for brevity
            break
            
    return suggestions

if __name__ == "__main__":
    print("Testing Transit Improvement Analysis")
    base_data_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    transit_data_file = base_data_path + r"\transit_data.json"
    # Road network can provide context but is not strictly essential for basic demand coverage
    # road_data_file = base_data_path + r"\road_data.json"
    # facilities_data_file = base_data_path + r"\facilities.json"

    transit_data_content = load_json_data(transit_data_file)
    # road_net_graph = get_base_road_network_for_transit(road_data_file, facilities_data_file) # Optional here

    if transit_data_content:
        print("\n--- Analyzing Demand Coverage (Based on existing routes/allocations) ---")
        coverage_results = analyze_demand_coverage(transit_data_content)
        if "error" not in coverage_results:
            print(f"Total Daily Public Transport Demand: {coverage_results["total_daily_demand_passengers"]} passengers")
            print(f"Directly Covered by Any Service: {coverage_results["passengers_directly_covered_by_any_service"]} ({coverage_results["percentage_any_direct_coverage"]}%)")
            print(f"  - By Metro (Direct): {coverage_results["passengers_directly_covered_by_metro"]} ({coverage_results["percentage_metro_direct_coverage"]}%)")
            print(f"  - By Bus (Direct): {coverage_results["passengers_directly_covered_by_bus"]} ({coverage_results["percentage_bus_direct_coverage"]}%)")
            print(f"Number of O-D Pairs with No Direct Coverage: {coverage_results["number_of_uncovered_od_pairs"]}")
            print(f"Total Passengers in Uncovered O-D Pairs: {coverage_results["total_passengers_in_uncovered_od_pairs"]}")
            print("\nTop Uncovered Demand Pairs:")
            for i, pair in enumerate(coverage_results.get("top_10_uncovered_demand_pairs", [])[:5]):
                print(f"  {i+1}. From {pair["FromID"]} to {pair["ToID"]}: {pair["Daily_Passengers"]} passengers")
            
            print("\n--- Conceptual Suggestions for Improvement ---")
            # Pass None for road_network_graph if not loaded/needed for this conceptual step
            improvement_suggestions = suggest_route_extensions_or_new_routes(coverage_results, transit_data_content, None) 
            for i, sug in enumerate(improvement_suggestions):
                print(f"  Suggestion {i+1}: {sug}")

        else:
            print(f"Error in demand coverage analysis: {coverage_results["error"]}")
        
        # Example: If you had optimized bus allocations from transit_optimization.py
        # optimized_buses = { ... } # load or pass this data
        # print("\n--- Analyzing Demand Coverage (With Optimized Bus Allocations) ---")
        # coverage_optimized = analyze_demand_coverage(transit_data_content, optimized_bus_allocations=optimized_buses)
        # ... print results for coverage_optimized ...

    else:
        print("Failed to load transit data for improvement analysis.")

