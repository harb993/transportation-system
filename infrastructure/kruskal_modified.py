import json
import networkx as nx
import heapq

# --- Data Loading ---
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

def get_infrastructure_graph(road_data_path, facilities_data_path):
    """Constructs a graph from road and facility data."""
    road_data = load_json_data(road_data_path)
    facilities_data = load_json_data(facilities_data_path)

    if not road_data or not facilities_data:
        return None

    graph = nx.Graph()

    if "nodes" in road_data:
        for node_info in road_data["nodes"]:
            node_id = str(node_info["ID"])
            graph.add_node(node_id, **node_info)

    if "facilities" in facilities_data:
        for facility_info in facilities_data["facilities"]:
            facility_id = str(facility_info["ID"])
            if facility_id not in graph:
                graph.add_node(facility_id, **facility_info)
            else:
                graph.nodes[facility_id].update(facility_info)

    if "edges" in road_data:
        seen_edges = set()
        for edge_info in road_data["edges"]:
            u, v = str(edge_info["FromID"]), str(edge_info["ToID"])
            edge_key = tuple(sorted([u, v]))
            if edge_key in seen_edges:
                print(f"Warning: Duplicate edge found between {u} and {v}, ignoring duplicate")
                continue
            seen_edges.add(edge_key)

            attributes = {}
            if edge_info.get("status") == "existing":
                attributes["distance_km"] = float(edge_info.get("Distance_km", float("inf")))
                attributes["capacity_veh_hr"] = int(edge_info.get("Current_Capacity_vehicles_hour", 0))
                attributes["condition"] = int(edge_info.get("Condition_1_10", 0))
                attributes["type"] = "existing_road"
            elif edge_info.get("status") == "potential":
                attributes["distance_km"] = float(edge_info.get("Distance_km", float("inf")))
                attributes["cost_million_egp"] = float(edge_info.get("Construction_Cost_Million_EGP", float("inf")))
                attributes["potential_capacity_veh_hr"] = int(edge_info.get("Estimated_Capacity_vehicles_hour", 0))
                attributes["type"] = "potential_road"

            attributes["original_from_id"] = u
            attributes["original_to_id"] = v
            graph.add_edge(u, v, **attributes)

    return graph

# --- Kruskal's Algorithm (Modified) ---
def kruskal_mst_modified(graph, weight_key="distance_km", consider_potential_roads=False,
                         critical_facility_ids=None, high_population_threshold=100000,
                         population_weight_factor=0.1):
    """Finds a Minimum Spanning Tree using Kruskal's algorithm with modifications."""
    if graph is None:
        return nx.Graph()

    mst = nx.Graph()
    mst.add_nodes_from(graph.nodes(data=True))

    # Print graph edge composition before filtering
    existing_count = sum(1 for _, _, d in graph.edges(data=True) if d.get("type") == "existing_road")
    potential_count = sum(1 for _, _, d in graph.edges(data=True) if d.get("type") == "potential_road")
    print(f"\nInitial graph composition:")
    print(f"- Existing roads: {existing_count}")
    print(f"- Potential roads: {potential_count}")
    print(f"- Total edges: {graph.number_of_edges()}")
    print(f"Consider potential roads: {consider_potential_roads}")

    components = list(nx.connected_components(graph))
    print(f"Number of connected components: {len(components)}")
    for i, component in enumerate(components):
        print(f"Component {i+1} has {len(component)} nodes: {', '.join(sorted(component))}")

    edges = []
    filtered_edges = 0
    added_edges = 0
    for u, v, data in graph.edges(data=True):
        if not consider_potential_roads and data.get("type") == "potential_road":
            filtered_edges += 1
            continue
        
        added_edges += 1
        road_type = data.get("type", "unknown")

        # Handle weight based on the weight_key
        if weight_key == "cost_million_egp":
            if data.get("type") == "existing_road":
                # Add a small distance-based penalty to existing roads to balance with potential roads
                original_weight = 0.0 + (float(data.get("distance_km", 0)) * 0.1)  # Small penalty: 0.1 * distance
            else:
                if "cost_million_egp" not in data:
                    print(f"Warning: No cost_million_egp for edge {u}-{v}, skipping")
                    continue
                original_weight = float(data["cost_million_egp"])
        else:
            if weight_key not in data:
                print(f"Warning: No {weight_key} for edge {u}-{v}, skipping")
                continue
            original_weight = float(data[weight_key])

        modified_weight = original_weight
        if data.get("type") == "potential_road" and weight_key == "distance_km" and "cost_million_egp" in data:
            cost_penalty = data["cost_million_egp"] / 100
            modified_weight = original_weight * (1 + cost_penalty)
            print(f"Potential road {u}-{v}: original weight={original_weight:.2f}, cost penalty={cost_penalty:.2f}, modified={modified_weight:.2f}")

        priority_multiplier = 1.0
        if critical_facility_ids and (u in critical_facility_ids or v in critical_facility_ids):
            priority_multiplier *= 0.8
        u_pop = graph.nodes[u].get("Population", 0)
        v_pop = graph.nodes[v].get("Population", 0)
        max_pop = max(u_pop, v_pop)
        if max_pop > high_population_threshold and high_population_threshold > 0:
            pop_factor = min(1.5, max_pop / high_population_threshold)
            priority_multiplier *= (1 - (population_weight_factor * (pop_factor - 1)))

        modified_weight *= priority_multiplier
        heapq.heappush(edges, (modified_weight, u, v, data))
    
    print(f"\nEdge filtering summary:")
    print(f"- Filtered edges: {filtered_edges}")
    print(f"- Added to heap: {added_edges}")
    print(f"- Total processed: {filtered_edges + added_edges}")

    parent = {node: node for node in graph.nodes()}
    def find_set(node):
        if parent[node] != node:
            parent[node] = find_set(parent[node])
        return parent[node]

    def unite_sets(u_set, v_set):
        parent[u_set] = v_set

    num_edges_in_mst = 0
    target_num_edges = graph.number_of_nodes() - 1
    if graph.number_of_nodes() == 0:
        return mst

    while edges and num_edges_in_mst < target_num_edges:
        weight, u, v, edge_data = heapq.heappop(edges)
        u_set, v_set = find_set(u), find_set(v)
        if u_set != v_set:
            mst.add_edge(u, v, **edge_data, modified_weight=weight, original_weight=edge_data.get(weight_key, 0.0))
            unite_sets(u_set, v_set)
            num_edges_in_mst += 1
            if not nx.is_connected(mst) and num_edges_in_mst == target_num_edges:
                break

    print(f"MST edges added: {num_edges_in_mst}")
    return mst

if __name__ == "__main__":
    print("Testing Kruskal Modified MST at 04:28 AM EEST on Monday, May 19, 2025")
    base_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    road_data_file = base_path + r"\road_data.json"
    facilities_data_file = base_path + r"\facilities.json"

    infra_graph = get_infrastructure_graph(road_data_file, facilities_data_file)

    if infra_graph:
        print(f"Infrastructure graph loaded: {infra_graph.number_of_nodes()} nodes, {infra_graph.number_of_edges()} edges")

        # Test 1: Basic MST with distance on existing roads
        mst1 = kruskal_mst_modified(infra_graph, weight_key="distance_km", consider_potential_roads=False)
        if mst1.edges():
            total_dist1 = sum(d["distance_km"] for u, v, d in mst1.edges(data=True))
            print(f"MST 1 (Distance, Existing): {mst1.number_of_edges()} edges, Total Distance: {total_dist1:.2f} km")
            print("Edges in MST 1:")
            for u, v, data in sorted(mst1.edges(data=True), key=lambda x: x[2]["distance_km"]):
                print(f"  {u}-{v}: {data['distance_km']} km (Existing)")
        else:
            print("MST 1: No edges found.")

        # Test 2: MST with cost on potential roads, prioritizing critical facilities
        mst2 = kruskal_mst_modified(infra_graph, weight_key="cost_million_egp",
                                    consider_potential_roads=True,
                                    critical_facility_ids=["F9", "F10"],
                                    high_population_threshold=300000,
                                    population_weight_factor=0.2)
        if mst2.edges():
            total_cost2 = sum(d["cost_million_egp"] for u, v, d in mst2.edges(data=True) if "cost_million_egp" in d and d.get("type") == "potential_road")
            total_dist_existing_mst2 = sum(d["distance_km"] for u, v, d in mst2.edges(data=True) if "distance_km" in d and d.get("type") == "existing_road")
            total_dist_potential_mst2 = sum(d["distance_km"] for u, v, d in mst2.edges(data=True) if "distance_km" in d and d.get("type") == "potential_road")
            print(f"MST 2 (Cost-Potential, Prioritized): {mst2.number_of_edges()} edges. Total Potential Cost: {total_cost2:.2f} M EGP. Total Existing Distance: {total_dist_existing_mst2:.2f} km. Total Potential Distance: {total_dist_potential_mst2:.2f} km")
            print("Edges in MST 2:")
            for u, v, data in sorted(mst2.edges(data=True), key=lambda x: (x[2]["type"], x[2].get("cost_million_egp", x[2]["distance_km"]))):
                road_type = data["type"]
                if road_type == "potential_road":
                    print(f"  {u}-{v}: {data['cost_million_egp']} M EGP, {data['distance_km']} km (Potential)")
                else:
                    print(f"  {u}-{v}: {data['distance_km']} km (Existing)")
        else:
            print("MST 2: No edges found.")

        # Test 3: MST with distance, including potential roads and prioritization
        mst3 = kruskal_mst_modified(infra_graph, weight_key="distance_km",
                                    consider_potential_roads=True,
                                    critical_facility_ids=["F9"],
                                    high_population_threshold=200000,
                                    population_weight_factor=0.15)
        if mst3.edges():
            total_dist3 = sum(d["distance_km"] for u, v, d in mst3.edges(data=True))
            print(f"MST 3 (Distance, All Roads, Prioritized): {mst3.number_of_edges()} edges, Total Distance: {total_dist3:.2f} km")
            print("Edges in MST 3:")
            for u, v, data in sorted(mst3.edges(data=True), key=lambda x: x[2]["distance_km"]):
                print(f"  {u}-{v}: {data['distance_km']} km ({data['type'].replace('_road', '')})")
        else:
            print("MST 3: No edges found.")
    else:
        print("Failed to load infrastructure graph for testing.")