import json
import networkx as nx
import heapq
import math

# --- Data Loading (Shared logic) ---
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

def get_emergency_graph(road_data_path, facilities_data_path, traffic_data_path):
    road_data = load_json_data(road_data_path)
    facilities_data = load_json_data(facilities_data_path)
    traffic_data = load_json_data(traffic_data_path)

    if not road_data:
        print("Error: Road data not found for emergency graph.")
        return None

    graph = nx.DiGraph()

    # Add nodes from road_data (neighborhoods)
    if "nodes" in road_data:
        for node_info in road_data["nodes"]:
            node_id = str(node_info["ID"])
            graph.add_node(node_id, **node_info)
    
    # Add nodes from facilities_data
    if facilities_data:
        for facility_info in facilities_data:
            facility_id = str(facility_info["ID"])
            if facility_id not in graph:
                graph.add_node(facility_id, **facility_info)
            else:
                graph.nodes[facility_id].update(facility_info)

    # Add edges from road_data
    if "edges" in road_data:
        for edge_info in road_data["edges"]:
            u, v = str(edge_info["FromID"]), str(edge_info["ToID"])
            if not graph.has_node(u): graph.add_node(u, ID=u, Name=f"Node {u}")
            if not graph.has_node(v): graph.add_node(v, ID=v, Name=f"Node {v}")
            
            attrs = {
                "distance_km": float(edge_info.get("Distance_km", float("inf"))),
                "base_capacity_veh_hr": int(edge_info.get("Current_Capacity_vehicles_hour", 
                                                          edge_info.get("Estimated_Capacity_vehicles_hour", 1000))),
                "status": edge_info.get("status", "unknown")
            }
            # Add edges in both directions for emergency access
            graph.add_edge(u, v, **attrs)
            graph.add_edge(v, u, **attrs)  # Add reverse direction

    # Augment with traffic data for time-dependent considerations
    if traffic_data:
        for traffic_entry in traffic_data:
            u, v = str(traffic_entry["RoadID_From"]), str(traffic_entry["RoadID_To"])
            if graph.has_edge(u, v):
                for key, val in traffic_entry.items():
                    if key not in ["RoadID_From", "RoadID_To"]:
                        graph[u][v][key.lower()] = int(val)
    return graph

# --- A* Algorithm for Emergency Routing ---
def heuristic_distance(graph, node1_id, node2_id):
    """Euclidean distance heuristic using X_coordinate and Y_coordinate."""
    node1_data = graph.nodes.get(node1_id, {})
    node2_data = graph.nodes.get(node2_id, {})
    
    x1 = node1_data.get("X_coordinate")
    y1 = node1_data.get("Y_coordinate")
    x2 = node2_data.get("X_coordinate")
    y2 = node2_data.get("Y_coordinate")

    if all(coord is not None for coord in [x1, y1, x2, y2]):
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
    return 0 # Default if coordinates are missing

def a_star_emergency_path(graph, source, target, weight_key="distance_km", 
                            time_dependent=False, time_of_day=None, 
                            emergency_priority_factor=1.0):
    """
    Finds the shortest path using A* for emergency services.
    Args:
        graph (nx.DiGraph): The input graph.
        source: Starting node ID.
        target: Destination node ID.
        weight_key (str): Base edge attribute for weight (e.g., "distance_km").
        time_dependent (bool): Whether to use time-dependent traffic data.
        time_of_day (str): "morning_peak", "afternoon", "evening_peak", or "night".
        emergency_priority_factor (float): Factor to adjust perceived travel time/distance for emergency.
                                           Values < 1 make path appear shorter/faster.
    Returns:
        list: List of nodes in the shortest path, or None.
        float: Total path length (effective, considering priority), or None.
    """
    if graph is None or not graph.has_node(source) or not graph.has_node(target):
        print("Error: Invalid graph or source/target node for A*.")
        return None, None

    def get_dynamic_edge_weight(u, v, data):
        base_weight = data.get(weight_key, float("inf"))
        effective_weight = base_weight

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
                capacity = data.get("base_capacity_veh_hr", 1)
                if capacity == 0: capacity = 1
                
                # For emergency, high congestion might be less of a deterrent or handled differently
                # Simple model: still consider congestion but perhaps less impactful than normal routing
                congestion_factor = 1 + (traffic_flow / (capacity * 1.5)) # Assume emergency can bypass some congestion
                congestion_factor = min(congestion_factor, 3.0) # Cap factor
                effective_weight = base_weight * congestion_factor
        
        # Apply emergency priority factor
        return effective_weight * emergency_priority_factor

    try:
        path = nx.astar_path(graph, source, target, 
                             heuristic=lambda u,v: heuristic_distance(graph, u,v) * emergency_priority_factor,
                             weight=lambda u,v,data: get_dynamic_edge_weight(u,v,data))
        
        # Calculate actual path length based on the dynamic weights used
        length = 0
        for i in range(len(path) - 1):
            u_node, v_node = path[i], path[i+1]
            edge_data = graph.get_edge_data(u_node, v_node)
            length += get_dynamic_edge_weight(u_node, v_node, edge_data)
            
        return path, length
    except nx.NetworkXNoPath:
        print(f"No A* path found between {source} and {target}.")
        return None, None
    except Exception as e:
        print(f"Error in A* emergency path: {e}")
        return None, None

def analyze_path_options(graph, source, target):
    """Analyze and print all possible paths between two nodes."""
    print(f"\nAnalyzing all possible paths between {source} and {target}:")
    try:
        # Try Dijkstra first as it's usually faster
        try:
            dijkstra_path = nx.dijkstra_path(graph, source, target, weight="distance_km")
            dist = sum(graph[dijkstra_path[i]][dijkstra_path[i+1]].get("distance_km",0) 
                      for i in range(len(dijkstra_path)-1))
            print(f"Dijkstra shortest path: {dijkstra_path}")
            print(f"Distance: {dist:.2f} km")
        except nx.NetworkXNoPath:
            print("No path found using Dijkstra's algorithm")
            
        # Try to find all simple paths (limited to prevent excessive computation)
        paths = list(nx.shortest_simple_paths(graph, source, target, weight="distance_km"))
        if paths:
            print(f"\nFound paths (ordered by distance):")
            for i, path in enumerate(paths[:5], 1):  # Show top 5 paths
                dist = sum(graph[path[i]][path[i+1]].get("distance_km",0) 
                          for i in range(len(path)-1))
                print(f"Path {i}: {path}, Distance: {dist:.2f} km")
        else:
            print("No simple paths found")
            
        # Check graph connectivity
        print("\nChecking graph connectivity:")
        if nx.is_strongly_connected(graph):
            print("Graph is strongly connected")
        else:
            components = list(nx.strongly_connected_components(graph))
            print(f"Graph has {len(components)} strongly connected components")
            # Find which components contain our nodes
            source_comp = target_comp = None
            for i, comp in enumerate(components):
                if source in comp:
                    source_comp = i
                    print(f"Source node is in component {i} with {len(comp)} nodes")
                if target in comp:
                    target_comp = i
                    print(f"Target node is in component {i} with {len(comp)} nodes")
            
            # If nodes are in different components, find possible connecting nodes
            if source_comp != target_comp and source_comp is not None and target_comp is not None:
                print("\nAnalyzing possible connecting paths between components:")
                source_neighbors = set(graph.neighbors(source))
                target_predecessors = set(graph.predecessors(target))
                print(f"Source node neighbors: {source_neighbors}")
                print(f"Target node predecessors: {target_predecessors}")
                common_nodes = source_neighbors & target_predecessors
                if common_nodes:
                    print(f"Common nodes that might help connect the path: {common_nodes}")
                
    except Exception as e:
        print(f"Error analyzing paths: {e}")

if __name__ == "__main__":
    print("Testing A* Emergency Routing")
    base_data_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    road_file = base_data_path + r"\road_data.json"
    facilities_file = base_data_path + r"\facilities.json"
    traffic_file = base_data_path + r"\traffic_data.json"

    emergency_graph_net = get_emergency_graph(road_file, facilities_file, traffic_file)

    if emergency_graph_net:
        print(f"Emergency graph loaded: {emergency_graph_net.number_of_nodes()} nodes, {emergency_graph_net.number_of_edges()} edges")
        
        # Example: Emergency from a residential area to a hospital
        source_loc, target_hospital = "2", "F9" # Nasr City to Qasr El Aini Hospital

        if not emergency_graph_net.has_node(source_loc) or not emergency_graph_net.has_node(target_hospital):
            print(f"Source ({source_loc}) or Target ({target_hospital}) node not in graph.")
        else:
            analyze_path_options(emergency_graph_net, source_loc, target_hospital)
            
            print(f"\nRouting from {emergency_graph_net.nodes[source_loc].get('Name', source_loc)} to {emergency_graph_net.nodes[target_hospital].get('Name', target_hospital)}")
            
            # Try to find paths using different algorithms
            analyze_path_options(emergency_graph_net, source_loc, target_hospital)
            
            # Test 1: A* with base distance, high priority
            path1, len1 = a_star_emergency_path(emergency_graph_net, source_loc, target_hospital, 
                                                weight_key="distance_km", emergency_priority_factor=0.8)
            if path1:
                actual_dist1 = sum(emergency_graph_net[path1[i]][path1[i+1]].get("distance_km",0) for i in range(len(path1)-1))
                print(f"  A* Path (Distance, High Prio): {path1}")
                print(f"    Effective Length (for A*): {len1:.2f}, Actual Distance: {actual_dist1:.2f} km")

            # Test 2: A* with time-dependent (evening peak), medium priority
            path2, len2 = a_star_emergency_path(emergency_graph_net, source_loc, target_hospital, 
                                                weight_key="distance_km", time_dependent=True, 
                                                time_of_day="evening_peak", emergency_priority_factor=0.9)
            if path2:
                actual_dist2 = sum(emergency_graph_net[path2[i]][path2[i+1]].get("distance_km",0) for i in range(len(path2)-1))
                print(f"  A* Path (Evening Peak, Med Prio): {path2}")
                print(f"    Effective Length (for A*): {len2:.2f}, Actual Distance: {actual_dist2:.2f} km")

            # Test 3: A* with time-dependent (night), no explicit priority factor (factor=1)
            path3, len3 = a_star_emergency_path(emergency_graph_net, source_loc, target_hospital, 
                                                weight_key="distance_km", time_dependent=True, 
                                                time_of_day="night", emergency_priority_factor=1.0)
            if path3:
                actual_dist3 = sum(emergency_graph_net[path3[i]][path3[i+1]].get("distance_km",0) for i in range(len(path3)-1))
                print(f"  A* Path (Night, Normal Prio): {path3}")
                print(f"    Effective Length (for A*): {len3:.2f}, Actual Distance: {actual_dist3:.2f} km")
    else:
        print("Failed to load graph for A* emergency routing testing.")

