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

def get_infrastructure_graph_for_cost(road_data_path, facilities_data_path):
    """Constructs a graph focusing on attributes relevant for cost analysis."""
    road_data = load_json_data(road_data_path)
    facilities_data = load_json_data(facilities_data_path)

    if not road_data:
        print("Error: Road data not found for cost analysis.")
        return None

    graph = nx.Graph()

    if "nodes" in road_data:
        for node_info in road_data["nodes"]:
            node_id = str(node_info["ID"])
            graph.add_node(node_id, **node_info)

    if facilities_data and "facilities" in facilities_data:
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

            attributes = edge_info.copy()
            if "Construction_Cost_Million_EGP" in attributes:
                attributes["Construction_Cost_Million_EGP"] = float(attributes["Construction_Cost_Million_EGP"])
            if "Distance_km" in attributes:
                attributes["distance_km"] = float(attributes["Distance_km"])
            if edge_info.get("status") == "existing":
                attributes["type"] = "existing_road"
            elif edge_info.get("status") == "potential":
                attributes["type"] = "potential_road"
            else:
                attributes["type"] = "unknown"

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

    components = list(nx.connected_components(graph))
    print(f"Number of connected components: {len(components)}")
    for i, component in enumerate(components):
        print(f"Component {i+1} has {len(component)} nodes: {', '.join(sorted(component))}")

    edges = []
    for u, v, data in graph.edges(data=True):
        if not consider_potential_roads and data.get("status") == "potential":
            continue

        # Handle weight based on the weight_key
        if weight_key == "Construction_Cost_Million_EGP":
            if data.get("status") == "existing":
                # Add a small distance-based penalty to existing roads
                original_weight = 0.0 + (float(data.get("distance_km", 0)) * 0.1)
            else:
                if "Construction_Cost_Million_EGP" not in data:
                    print(f"Warning: No Construction_Cost_Million_EGP for edge {u}-{v}, skipping")
                    continue
                original_weight = float(data["Construction_Cost_Million_EGP"])
        else:
            if weight_key not in data:
                print(f"Warning: No {weight_key} for edge {u}-{v}, skipping")
                continue
            original_weight = float(data[weight_key])

        modified_weight = original_weight
        if data.get("status") == "potential" and weight_key == "distance_km" and "Construction_Cost_Million_EGP" in data:
            cost_penalty = data["Construction_Cost_Million_EGP"] / 100
            modified_weight = original_weight * (1 + cost_penalty)

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
            mst.add_edge(u, v, **edge_data, modified_weight=weight)
            unite_sets(u_set, v_set)
            num_edges_in_mst += 1
            if not nx.is_connected(mst) and num_edges_in_mst == target_num_edges:
                break

    print(f"MST edges added: {num_edges_in_mst}")
    return mst

# --- Cost Analysis Functions ---
def analyze_potential_road_costs(graph):
    """Analyzes and summarizes costs of potential new roads."""
    if graph is None:
        return {}
    potential_roads = []
    total_potential_cost = 0
    total_potential_distance = 0
    count = 0
    for u, v, data in graph.edges(data=True):
        if data.get("status") == "potential":
            cost = data.get("Construction_Cost_Million_EGP", 0)
            distance = data.get("distance_km", 0)
            potential_roads.append({
                "from": u, "to": v, "cost_million_egp": cost, "distance_km": distance,
                "estimated_capacity": data.get("Estimated_Capacity_vehicles_hour")
            })
            total_potential_cost += cost
            total_potential_distance += distance
            count += 1
    return {
        "count": count, "total_potential_cost_million_egp": total_potential_cost,
        "average_potential_cost_million_egp": total_potential_cost / count if count > 0 else 0,
        "total_potential_distance_km": total_potential_distance,
        "average_potential_distance_km": total_potential_distance / count if count > 0 else 0,
        "potential_roads_list": sorted(potential_roads, key=lambda x: x["cost_million_egp"], reverse=True)
    }

def analyze_mst_cost(mst_graph, original_graph, cost_attribute="Construction_Cost_Million_EGP", distance_attribute="distance_km"):
    """Analyzes the cost and distance of a given MST or road selection, including isolated nodes."""
    if mst_graph is None or mst_graph.number_of_edges() == 0:
        return {"total_cost": 0, "total_distance": 0, "edge_count": 0, "details": [], "isolated_nodes": []}

    total_cost = 0
    total_distance = 0
    edge_details = []
    for u, v, data in mst_graph.edges(data=True):
        current_cost = data.get(cost_attribute, 0) if data.get("status") == "potential" else 0
        current_distance = data.get(distance_attribute, 0)
        total_cost += current_cost
        total_distance += current_distance
        edge_details.append({
            "from": u, "to": v, "cost": current_cost, "distance": current_distance,
            "type": data.get("type", "unknown"), "original_weight": data.get("modified_weight", 0)
        })

    # Identify isolated nodes (nodes with degree 0 in the original graph)
    isolated_nodes = [node for node in original_graph.nodes() if original_graph.degree(node) == 0]

    return {
        "total_construction_cost_million_egp": total_cost,
        "total_network_distance_km": total_distance,
        "edge_count": mst_graph.number_of_edges(),
        "edge_details": edge_details,
        "isolated_nodes": isolated_nodes
    }

if __name__ == "__main__":
    print("Testing Infrastructure Cost Analysis at 04:28 AM EEST on Monday, May 19, 2025")
    base_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    output_path = r"c:\Users\abdoo\Desktop\transportation_system\output\reports\cost_summary.txt"
    road_data_file = base_path + r"\road_data.json"
    facilities_data_file = base_path + r"\facilities.json"

    infra_graph = get_infrastructure_graph_for_cost(road_data_file, facilities_data_file)

    with open(output_path, 'w') as f:
        if infra_graph:
            f.write(f"Infrastructure Analysis Report\n")
            f.write(f"===========================\n\n")
            f.write(f"Network Overview:\n")
            f.write(f"- Total nodes: {infra_graph.number_of_nodes()}\n")
            f.write(f"- Total edges: {infra_graph.number_of_edges()}\n\n")

            potential_costs_summary = analyze_potential_road_costs(infra_graph)
            f.write("Potential Road Costs Summary\n")
            f.write("---------------------------\n")
            f.write(f"Number of potential road projects: {potential_costs_summary['count']}\n")
            f.write(f"Total estimated cost: {potential_costs_summary['total_potential_cost_million_egp']:.2f} M EGP\n")
            f.write(f"Average cost per project: {potential_costs_summary['average_potential_cost_million_egp']:.2f} M EGP\n")
            f.write(f"Total distance of potential roads: {potential_costs_summary['total_potential_distance_km']:.2f} km\n")
            f.write(f"Average distance per road: {potential_costs_summary['average_potential_distance_km']:.2f} km\n\n")

            if potential_costs_summary["count"] > 0:
                f.write("Top 3 Most Expensive Potential Roads:\n")
                for i, road in enumerate(potential_costs_summary["potential_roads_list"][:3]):
                    f.write(f"{i+1}. From {road['from']} to {road['to']}:\n")
                    f.write(f"   Cost: {road['cost_million_egp']:.2f} M EGP\n")
                    f.write(f"   Distance: {road['distance_km']:.2f} km\n")
                    f.write(f"   Estimated Capacity: {road['estimated_capacity']} vehicles/hour\n\n")

            if infra_graph.number_of_edges() > 0:
                mst = kruskal_mst_modified(infra_graph, weight_key="distance_km", consider_potential_roads=True)
                mst_cost_summary = analyze_mst_cost(mst, infra_graph, cost_attribute="Construction_Cost_Million_EGP")
                f.write("\nMinimum Spanning Tree Analysis\n")
                f.write("-----------------------------\n")
                f.write(f"Number of edges in MST: {mst_cost_summary['edge_count']}\n")
                f.write(f"Total construction cost: {mst_cost_summary['total_construction_cost_million_egp']:.2f} M EGP\n")
                f.write(f"Total network distance: {mst_cost_summary['total_network_distance_km']:.2f} km\n")
                if mst_cost_summary["edge_count"] > 0:
                    f.write("MST Edge Details:\n")
                    for i, edge in enumerate(mst_cost_summary["edge_details"]):
                        f.write(f"{i+1}. From {edge['from']} to {edge['to']}:\n")
                        f.write(f"   Cost: {edge['cost']:.2f} M EGP\n")
                        f.write(f"   Distance: {edge['distance']:.2f} km\n")
                        f.write(f"   Type: {edge['type']}\n\n")
                if mst_cost_summary["isolated_nodes"]:
                    f.write("Isolated Nodes:\n")
                    for node in sorted(mst_cost_summary["isolated_nodes"]):
                        f.write(f"- {node}")
                        name = infra_graph.nodes[node].get("Name", "")
                        if name:
                            f.write(f" ({name})")
                        f.write("\n")
                    f.write(f"Total isolated nodes: {len(mst_cost_summary['isolated_nodes'])}\n")
        else:
            f.write("Failed to load infrastructure graph for cost analysis.\n")

    print(f"Cost analysis results have been saved to {output_path}")