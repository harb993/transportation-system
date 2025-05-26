import json
import networkx as nx
import heapq

# --- Data Loading (Shared logic, consider a common utility module later) ---
def load_json_data(file_path):
    """Loads data from a JSON file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Data file not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None

def get_traffic_graph(road_data_path, facilities_data_path, traffic_data_path):
    """Constructs a directed graph for traffic flow analysis."""
    road_data = load_json_data(road_data_path)
    facilities_data = load_json_data(facilities_data_path)
    traffic_data = load_json_data(traffic_data_path)

    if not road_data or not traffic_data:
        print("Error: Road or Traffic data not found for graph construction.")
        return None

    graph = nx.DiGraph() # Traffic flow is directed

    # Add nodes from road_data (neighborhoods)
    if "nodes" in road_data:
        for node_info in road_data["nodes"]:
            node_id = str(node_info["ID"])
            graph.add_node(node_id, **node_info)
    
    # Add nodes from facilities_data (if facilities_data is provided and not None)
    if facilities_data and "neighborhoods" in facilities_data:
        for facility_info in facilities_data["neighborhoods"]:
            facility_id = str(facility_info["ID"])
            if facility_id not in graph:
                graph.add_node(facility_id, **facility_info)
            else:
                graph.nodes[facility_id].update(facility_info)
            
            # Find the nearest road network node based on coordinates
            if "X_coordinate" in facility_info and "Y_coordinate" in facility_info:
                min_distance = float("inf")
                nearest_node = None
                facility_x = facility_info["X_coordinate"]
                facility_y = facility_info["Y_coordinate"]
                
                for node, data in graph.nodes(data=True):
                    if node.startswith("F"):  # Skip other facilities
                        continue
                    if "X_coordinate" in data and "Y_coordinate" in data:
                        dx = facility_x - data["X_coordinate"]
                        dy = facility_y - data["Y_coordinate"]
                        dist = (dx * dx + dy * dy) ** 0.5
                        if dist < min_distance:
                            min_distance = dist
                            nearest_node = node
                
                if nearest_node:
                    # Add bidirectional edges between facility and nearest node
                    # Using the actual calculated distance (in coordinate units, need to scale to km)
                    # Assuming 1 coordinate unit ≈ 100km for this example
                    distance = min_distance * 100  # Scale to approximate kilometers
                    graph.add_edge(facility_id, nearest_node, 
                                 distance_km=distance,
                                 base_capacity_veh_hr=2000,  # High capacity for access roads
                                 type="facility_access")
                    graph.add_edge(nearest_node, facility_id, 
                                 distance_km=distance,
                                 base_capacity_veh_hr=2000,
                                 type="facility_access")

    # Add edges from road_data, traffic data will augment these edges
    edge_attributes = {}
    if "edges" in road_data:
        for edge_info in road_data["edges"]:
            u, v = str(edge_info["FromID"]), str(edge_info["ToID"])
            # Ensure nodes exist
            if not graph.has_node(u): graph.add_node(u, ID=u, Name=f"Node {u}", Type="Unknown")
            if not graph.has_node(v): graph.add_node(v, ID=v, Name=f"Node {v}", Type="Unknown")
            
            attrs = {
                "distance_km": float(edge_info.get("Distance_km", float("inf"))),
                "base_capacity_veh_hr": int(edge_info.get("Current_Capacity_vehicles_hour", 
                                                          edge_info.get("Estimated_Capacity_vehicles_hour", 0))),
                "condition": int(edge_info.get("Condition_1_10", 0)),
                "status": edge_info.get("status", "unknown")
            }
            # Store attributes to be augmented by traffic data
            # For DiGraph, multiple edges between u,v are not default, so one edge represents the road.
            # If multiple roads exist, the data should reflect unique road IDs or use MultiDiGraph.
            # Assuming (FromID, ToID) is unique for a road segment for now.
            edge_attributes[(u,v)] = attrs
            graph.add_edge(u, v, **attrs) # Add with base attributes first

    # Augment edges with traffic flow data
    if traffic_data:
        for traffic_entry in traffic_data:
            u, v = str(traffic_entry["RoadID_From"]), str(traffic_entry["RoadID_To"])
            if graph.has_edge(u, v):
                graph[u][v]["morning_peak_veh_h"] = int(traffic_entry.get("Morning_Peak_veh_h", 0))
                graph[u][v]["afternoon_veh_h"] = int(traffic_entry.get("Afternoon_veh_h", 0))
                graph[u][v]["evening_peak_veh_h"] = int(traffic_entry.get("Evening_Peak_veh_h", 0))
                graph[u][v]["night_veh_h"] = int(traffic_entry.get("Night_veh_h", 0))
            else:
                print(f"Warning: Traffic data for non-existent edge ({u}-{v}). Skipping.")
    return graph

# --- Dijkstra with Time-Dependent Weights ---
def dijkstra_time_dependent(graph, source, target, weight_key="distance_km", 
                            time_dependent=False, time_of_day=None):
    """
    Finds the shortest path using Dijkstra, considering time-dependent traffic.
    Args:
        graph (nx.DiGraph): The input graph.
        source: Starting node ID.
        target: Destination node ID.
        weight_key (str): Base edge attribute for weight (e.g., "distance_km").
        time_dependent (bool): Whether to use time-dependent traffic data.
        time_of_day (str): "morning_peak", "afternoon", "evening_peak", or "night".
    Returns:
        list: List of nodes in the shortest path, or None.
        float: Total path length, or None.
    """
    if graph is None or not graph.has_node(source) or not graph.has_node(target):
        print("Error: Invalid graph or source/target node.")
        return None, None

    # Determine the actual weight to use for each edge
    def get_edge_weight(u, v, data):
        base_weight = data.get(weight_key, float("inf"))
        if time_dependent and time_of_day:
            traffic_col_map = {
                "morning_peak": "morning_peak_veh_h",
                "afternoon": "afternoon_veh_h",
                "evening_peak": "evening_peak_veh_h",
                "night": "night_veh_h"
            }
            traffic_attr = traffic_col_map.get(time_of_day)
            if traffic_attr and traffic_attr in data:
                traffic_flow = data[traffic_attr]
                capacity = data.get("base_capacity_veh_hr", 1) # Avoid division by zero
                if capacity == 0: capacity = 1 # if capacity is 0, assume minimal capacity
                
                # Simple congestion model: effective_weight = base_weight * (1 + traffic_flow / capacity)
                # More complex models (like BPR) could be used here.
                congestion_factor = 1 + (traffic_flow / capacity)
                # Cap congestion factor to avoid extreme weights, e.g., max factor of 5
                congestion_factor = min(congestion_factor, 5.0) 
                return base_weight * congestion_factor
        return base_weight

    try:
        # NetworkX Dijkstra uses a weight function if the string `weight` is callable
        path = nx.dijkstra_path(graph, source, target, weight=lambda u, v, data: get_edge_weight(u, v, data))
        
        # Calculate path length based on the dynamic weights used
        length = 0
        for i in range(len(path) - 1):
            u, v_node = path[i], path[i+1]
            edge_data = graph.get_edge_data(u, v_node)
            length += get_edge_weight(u, v_node, edge_data)
            
        return path, length
    except nx.NetworkXNoPath:
        print(f"No path found between {source} and {target}.")
        return None, None
    except Exception as e:
        print(f"Error in Dijkstra: {e}")
        return None, None

if __name__ == "__main__":
    print("Testing Dijkstra Time-Dependent Shortest Path")
    base_data_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    road_file = base_data_path + r"\road_data.json"
    facilities_file = base_data_path + r"\facilities.json"
    traffic_file = base_data_path + r"\traffic_data.json"

    traffic_net_graph = get_traffic_graph(road_file, facilities_file, traffic_file)

    if traffic_net_graph:
        print(f"Traffic graph loaded: {traffic_net_graph.number_of_nodes()} nodes, {traffic_net_graph.number_of_edges()} edges")
        
        source_node, target_node = "1", "4" # Example: Maadi to New Cairo

        if not traffic_net_graph.has_node(source_node) or not traffic_net_graph.has_node(target_node):
            print(f"Source ({source_node}) or Target ({target_node}) node not in graph. Check node IDs.")
        else:
            # Test 1: Shortest path by distance (no time dependency)
            path1, len1 = dijkstra_time_dependent(traffic_net_graph, source_node, target_node, weight_key="distance_km")
            if path1:
                print(f"Path (Distance): {path1}, Length: {len1:.2f} km")

            # Test 2: Shortest path considering morning peak traffic (time-dependent)
            path2, len2 = dijkstra_time_dependent(traffic_net_graph, source_node, target_node, 
                                                weight_key="distance_km", time_dependent=True, time_of_day="morning_peak")
            if path2:
                print(f"Path (Morning Peak): {path2}, Effective Length: {len2:.2f}")
            
            # Test 3: Shortest path considering night traffic (time-dependent)
            path3, len3 = dijkstra_time_dependent(traffic_net_graph, source_node, target_node, 
                                                weight_key="distance_km", time_dependent=True, time_of_day="night")
            if path3:
                print(f"Path (Night): {path3}, Effective Length: {len3:.2f}")
                
            # Test with a different source/target
            source_node_b, target_node_b = "F1", "F9" # Airport to Qasr El Aini Hospital
            if traffic_net_graph.has_node(source_node_b) and traffic_net_graph.has_node(target_node_b):
                path4, len4 = dijkstra_time_dependent(traffic_net_graph, source_node_b, target_node_b, 
                                                    weight_key="distance_km", time_dependent=True, time_of_day="evening_peak")
                if path4:
                    print(f"Path (Airport to Hospital, Evening Peak): {path4}, Effective Length: {len4:.2f}")
            else:
                print(f"Source ({source_node_b}) or Target ({target_node_b}) node not in graph for test 4.")
    else:
        print("Failed to load traffic graph for testing.")

