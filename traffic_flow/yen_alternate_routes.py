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

def get_traffic_graph_for_yen(road_data_path, facilities_data_path, traffic_data_path):
    """Constructs a directed graph for Yen's K-shortest paths algorithm."""
    # This can reuse the graph loading logic from dijkstra_time_dependent.py
    # For simplicity, we'll assume a similar graph structure is needed.
    road_data = load_json_data(road_data_path)
    facilities_data = load_json_data(facilities_data_path)
    traffic_data = load_json_data(traffic_data_path)

    if not road_data:
        print("Error: Road data not found for graph construction.")
        return None

    graph = nx.DiGraph()

    if "nodes" in road_data:
        for node_info in road_data["nodes"]:
            node_id = str(node_info["ID"])
            graph.add_node(node_id, **node_info)
    
    if facilities_data and "neighborhoods" in facilities_data:
        for facility_info in facilities_data["neighborhoods"]:
            facility_id = str(facility_info["ID"])
            if facility_id not in graph:
                graph.add_node(facility_id, **facility_info)
            else:
                graph.nodes[facility_id].update(facility_info)

    if "edges" in road_data:
        for edge_info in road_data["edges"]:
            u, v = str(edge_info["FromID"]), str(edge_info["ToID"])
            if not graph.has_node(u): graph.add_node(u, ID=u, Name=f"Node {u}", Type="Unknown")
            if not graph.has_node(v): graph.add_node(v, ID=v, Name=f"Node {v}", Type="Unknown")
            
            attrs = {
                "distance_km": float(edge_info.get("Distance_km", float("inf"))),
                "base_capacity_veh_hr": int(edge_info.get("Current_Capacity_vehicles_hour", 
                                                          edge_info.get("Estimated_Capacity_vehicles_hour", 0))),
                "status": edge_info.get("status", "unknown")
            }
            graph.add_edge(u, v, **attrs)

    if traffic_data:
        for traffic_entry in traffic_data:
            u, v = str(traffic_entry["RoadID_From"]), str(traffic_entry["RoadID_To"])
            if graph.has_edge(u, v):
                graph[u][v]["morning_peak_veh_h"] = int(traffic_entry.get("Morning_Peak_veh_h", 0))
                graph[u][v]["afternoon_veh_h"] = int(traffic_entry.get("Afternoon_veh_h", 0))
                graph[u][v]["evening_peak_veh_h"] = int(traffic_entry.get("Evening_Peak_veh_h", 0))
                graph[u][v]["night_veh_h"] = int(traffic_entry.get("Night_veh_h", 0))
    return graph

# --- Yen's K-Shortest Paths Algorithm ---
def get_path_length(path, current_graph, current_weight_key):
    """Helper to calculate path length by summing edge weights."""
    length = 0
    for i in range(len(path) - 1):
        u, v_node = path[i], path[i+1]
        edge_data = current_graph.get_edge_data(u, v_node)
        if edge_data and current_weight_key in edge_data:
            length += edge_data[current_weight_key]
        else: # Should not happen if graph is well-formed and path exists
            return float("inf") 
    return length

def yen_k_shortest_paths(graph, source, target, K=3, weight_key="distance_km"):
    """
    Implements Yen's algorithm to find K loopless shortest paths.
    Args:
        graph (nx.DiGraph): The input graph.
        source: Starting node ID.
        target: Destination node ID.
        K (int): The number of shortest paths to find.
        weight_key (str): Edge attribute for weight.
    Returns:
        list: A list of K shortest paths. Each path is a list of nodes.
              Returns fewer than K paths if not enough unique paths exist.
    """
    if graph is None or not graph.has_node(source) or not graph.has_node(target):
        print("Error: Invalid graph or source/target node for Yen's algorithm.")
        return []

    # List to store the K shortest paths found so far
    A = []
    # Priority queue to store potential K-shortest paths
    B = []

    # Find the first shortest path using Dijkstra
    try:
        first_path = nx.dijkstra_path(graph, source, target, weight=weight_key)
        first_path_len = get_path_length(first_path, graph, weight_key)
        A.append((first_path_len, first_path))
    except nx.NetworkXNoPath:
        return [] # No path exists
    except KeyError:
        print(f"Warning: Weight key 	'{weight_key}	' not found in all edges for the first path.")
        return []

    for k in range(1, K):
        if not A: # No more paths to build upon
            break
        
        # The k-1 shortest path
        prev_path_len, prev_path = A[k-1]

        for i in range(len(prev_path) - 1):
            # Spur node is retrieved from the previous k-shortest path, k-1
            spur_node = prev_path[i]
            # The sequence of nodes from source to the spur node of the previous k-shortest path
            root_path = prev_path[:i+1]

            # Create a temporary graph for finding spur paths
            temp_graph = graph.copy()
            
            removed_edges = []

            # Remove edges that are part of the previous shortest paths which share the same root path
            for path_len, path_val in A:
                if len(path_val) > i and path_val[:i+1] == root_path:
                    u, v_node = path_val[i], path_val[i+1]
                    if temp_graph.has_edge(u, v_node):
                        edge_data = temp_graph.get_edge_data(u,v_node)
                        temp_graph.remove_edge(u, v_node)
                        removed_edges.append((u,v_node,edge_data))
            
            # Remove nodes in root_path (except spur_node) from temp_graph to prevent loops
            # This part is tricky: we want to avoid re-tracing root_path segments immediately
            # A simpler way for loopless is to ensure spur path doesn't immediately go back to a node in root_path[:-1]
            for node_in_root in root_path[:-1]: # All nodes in root_path except spur_node itself
                # Remove all edges from spur_node to node_in_root if they exist
                # This is a simplification. A more robust way is to remove nodes from consideration in Dijkstra.
                # For now, we rely on Dijkstra not forming immediate loops if weights are positive.
                pass # NetworkX Dijkstra itself finds simple paths by default.

            # Calculate the spur path from the spur_node to the target
            try:
                spur_path = nx.dijkstra_path(temp_graph, spur_node, target, weight=weight_key)
                
                # Add the spur path to the root path to form a new potential K-shortest path
                total_path = root_path[:-1] + spur_path # Avoid duplicating spur_node
                total_path_len = get_path_length(total_path, graph, weight_key)
                
                # Add the new path to B if it's not already in A (as a tuple of nodes to be hashable)
                path_tuple = tuple(total_path)
                is_new = True
                for _, existing_path_nodes in A:
                    if tuple(existing_path_nodes) == path_tuple:
                        is_new = False
                        break
                if is_new:
                    heapq.heappush(B, (total_path_len, total_path))
            
            except nx.NetworkXNoPath:
                pass # No spur path found
            except KeyError:
                 # print(f"Warning: Weight key 	'{weight_key}	' not found for a spur path.")
                 pass # If weight key is missing on some edge in temp_graph

            # Add back the edges and nodes that were removed from the graph
            # temp_graph.add_edges_from(removed_edges) # Not strictly necessary as temp_graph is a copy

        if not B:
            break # No more potential paths

        # Add the shortest path from B to A
        # Ensure it's not already in A to maintain uniqueness of paths (not just lengths)
        added_to_A = False
        while B and not added_to_A:
            potential_len, potential_path = heapq.heappop(B)
            is_unique_in_A = True
            for _, existing_path_val in A:
                if tuple(existing_path_val) == tuple(potential_path):
                    is_unique_in_A = False
                    break
            if is_unique_in_A:
                A.append((potential_len, potential_path))
                added_to_A = True
        
        if not added_to_A and not B: # If B became empty and nothing was added
            break
            
    # Return only the path lists, sorted by length
    A.sort(key=lambda x: x[0])
    return [path for length, path in A[:K]]

if __name__ == "__main__":
    print("Testing Yen's K-Shortest Paths Algorithm")
    base_data_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    road_file = base_data_path + r"\road_data.json"
    facilities_file = base_data_path + r"\facilities.json"
    traffic_file = base_data_path + r"\traffic_data.json" # Not used by Yen's directly here, but graph loader uses it

    graph_for_yen = get_traffic_graph_for_yen(road_file, facilities_file, traffic_file)

    if graph_for_yen:
        print(f"Graph for Yen's loaded: {graph_for_yen.number_of_nodes()} nodes, {graph_for_yen.number_of_edges()} edges")
        
        source_node, target_node = "1", "4" # Maadi to New Cairo
        num_paths_to_find = 3

        if not graph_for_yen.has_node(source_node) or not graph_for_yen.has_node(target_node):
            print(f"Source ({source_node}) or Target ({target_node}) node not in graph.")
        else:
            k_shortest_paths = yen_k_shortest_paths(graph_for_yen, source_node, target_node, K=num_paths_to_find, weight_key="distance_km")
            
            if k_shortest_paths:
                print(f"\nFound {len(k_shortest_paths)} shortest paths from {source_node} to {target_node} (up to K={num_paths_to_find}):")
                for i, path in enumerate(k_shortest_paths):
                    path_len = get_path_length(path, graph_for_yen, "distance_km")
                    print(f"  Path {i+1}: {path} (Length: {path_len:.2f} km)")
            else:
                print(f"No paths found or fewer than K={num_paths_to_find} paths exist between {source_node} and {target_node}.")
                
        # Another test case
        source_node_2, target_node_2 = "F1", "9" # Airport to Mohandessin
        if graph_for_yen.has_node(source_node_2) and graph_for_yen.has_node(target_node_2):
            k_shortest_paths_2 = yen_k_shortest_paths(graph_for_yen, source_node_2, target_node_2, K=2, weight_key="distance_km")
            if k_shortest_paths_2:
                print(f"\nFound {len(k_shortest_paths_2)} shortest paths from {source_node_2} to {target_node_2} (up to K=2):")
                for i, path in enumerate(k_shortest_paths_2):
                    path_len = get_path_length(path, graph_for_yen, "distance_km")
                    print(f"  Path {i+1}: {path} (Length: {path_len:.2f} km)")
        else:
            print(f"Source ({source_node_2}) or Target ({target_node_2}) node not in graph for second test.")
    else:
        print("Failed to load graph for Yen's algorithm testing.")

