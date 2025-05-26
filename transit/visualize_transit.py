import json
import networkx as nx
import matplotlib.pyplot as plt
import random

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

def get_base_network_for_visualization(road_data_path, facilities_data_path):
    road_data = load_json_data(road_data_path)
    facilities_data = load_json_data(facilities_data_path)
    if not road_data:
        return None
    graph = nx.Graph()
    node_positions = {}
    node_types = {}

    if "nodes" in road_data:
        for node_info in road_data["nodes"]:
            node_id = str(node_info["ID"])
            graph.add_node(node_id, **node_info)
            if "X_coordinate" in node_info and "Y_coordinate" in node_info:
                node_positions[node_id] = (node_info["X_coordinate"], node_info["Y_coordinate"])
            node_types[node_id] = node_info.get("Type", "Unknown")
            
    if facilities_data:
        for facility_info in facilities_data:
            fid = str(facility_info["ID"])
            if fid not in graph:
                graph.add_node(fid, **facility_info)
            else:
                graph.nodes[fid].update(facility_info)
            if "X_coordinate" in facility_info and "Y_coordinate" in facility_info:
                node_positions[fid] = (facility_info["X_coordinate"], facility_info["Y_coordinate"])
            node_types[fid] = facility_info.get("Type", "Facility")

    # Add edges for context, but they won_t be the primary focus for transit lines
    if "edges" in road_data:
        for edge_info in road_data["edges"]:
            u, v = str(edge_info["FromID"]), str(edge_info["ToID"])
            if graph.has_node(u) and graph.has_node(v):
                graph.add_edge(u,v, type="road")
                
    return graph, node_positions, node_types

# --- Transit Visualization Functions ---
def visualize_transit_network(base_graph, node_pos, node_types_map,
                                metro_lines_data=None, bus_routes_data=None, 
                                title="Public Transit Network", output_path=None):
    if base_graph is None:
        print("Base graph not available for visualization.")
        return

    fig, ax = plt.subplots(figsize=(18, 15))
    
    # Use provided positions or generate new ones
    current_pos = node_pos if node_pos and len(node_pos) == base_graph.number_of_nodes() else nx.spring_layout(base_graph, k=0.3, iterations=30)

    # Draw base road network lightly for context
    nx.draw_networkx_edges(base_graph, current_pos, ax=ax, edge_color="lightgray", alpha=0.4, width=0.5)
    
    # Node colors based on type
    node_colors_list = []
    type_color_map = {"Residential": "lightblue", "Business": "lightgreen", "Mixed": "lightcoral", 
                      "Medical": "salmon", "Airport": "gold", "Transit Hub": "orange", 
                      "Facility": "wheat", "Unknown": "silver"}
    
    for node_id in base_graph.nodes():
        node_colors_list.append(type_color_map.get(node_types_map.get(node_id, "Unknown"), "silver"))

    nx.draw_networkx_nodes(base_graph, current_pos, ax=ax, node_size=50, node_color=node_colors_list, alpha=0.7)
    # nx.draw_networkx_labels(base_graph, current_pos, ax=ax, font_size=7, alpha=0.8)

    legend_elements = [
        plt.Line2D([0], [0], marker="o", color="w", label=ntype, markerfacecolor=color, markersize=8)
        for ntype, color in type_color_map.items() if ntype in set(node_types_map.values())
    ]

    # Plot Metro Lines
    metro_colors = ["red", "blue", "green", "purple", "brown"]
    if metro_lines_data:
        for i, line in enumerate(metro_lines_data):
            stations = line.get("Stations_comma_separated_IDs", [])
            if len(stations) > 1:
                line_path_edges = list(zip(stations[:-1], stations[1:]))
                # Check if all stations in path exist in graph
                valid_path_edges = [(u,v) for u,v in line_path_edges if base_graph.has_node(u) and base_graph.has_node(v)]
                nx.draw_networkx_edges(base_graph, current_pos, edgelist=valid_path_edges, 
                                       ax=ax, edge_color=metro_colors[i % len(metro_colors)], 
                                       width=3.5, alpha=0.8, style="solid")
                # Highlight metro stations
                nx.draw_networkx_nodes(base_graph, current_pos, nodelist=[s for s in stations if base_graph.has_node(s)], 
                                     ax=ax, node_size=100, node_color=metro_colors[i % len(metro_colors)], 
                                     edgecolors="black")
                legend_elements.append(plt.Line2D([0], [0], color=metro_colors[i % len(metro_colors)], lw=3, label=f"Metro: {line.get('Name', line['LineID'])}"))

    # Plot Bus Routes
    bus_colors = ["darkorange", "deepskyblue", "limegreen", "magenta", "teal"]
    if bus_routes_data:
        for i, route in enumerate(bus_routes_data):
            stops = route.get("Stops_comma_separated_IDs", [])
            if len(stops) > 1:
                route_path_edges = list(zip(stops[:-1], stops[1:]))
                valid_route_edges = [(u,v) for u,v in route_path_edges if base_graph.has_node(u) and base_graph.has_node(v)]
                nx.draw_networkx_edges(base_graph, current_pos, edgelist=valid_route_edges, 
                                       ax=ax, edge_color=bus_colors[i % len(bus_colors)], 
                                       width=1.8, alpha=0.7, style="dashed")
                # Highlight bus stops (if not already metro stations)
                bus_stop_nodes = [s for s in stops if base_graph.has_node(s)]
                nx.draw_networkx_nodes(base_graph, current_pos, nodelist=bus_stop_nodes, 
                                     ax=ax, node_size=60, node_color=bus_colors[i % len(bus_colors)], 
                                     alpha=0.6)
                if i < 3: # Add legend for first few bus routes for clarity
                    legend_elements.append(plt.Line2D([0], [0], color=bus_colors[i % len(bus_colors)], lw=2, linestyle="--", label=f"Bus: {route["RouteID"]}"))
        if len(bus_routes_data) > 3:
             legend_elements.append(plt.Line2D([0], [0], color="gray", lw=2, linestyle="--", label="Other Bus Routes"))

    plt.title(title, fontsize=18)
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9)
    plt.axis("off")

    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, bbox_inches="tight")
        print(f"Transit network visualization saved to {output_path}")
    else:
        plt.show()
    plt.close(fig)

if __name__ == "__main__":
    print("Testing Transit Network Visualization")
    base_data_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    output_viz_path = r"c:\Users\abdoo\Desktop\transportation_system\output\visualizations\transit_map.png"
    
    # Ensure output directory exists
    import os
    os.makedirs(os.path.dirname(output_viz_path), exist_ok=True)

    road_file = base_data_path + r"\road_data.json"
    facilities_file = base_data_path + r"\facilities.json"
    transit_file = base_data_path + r"\transit_data.json"

    base_net, node_positions_data, node_type_data = get_base_network_for_visualization(road_file, facilities_file)
    transit_data = load_json_data(transit_file)

    if base_net and transit_data:
        metro_data = transit_data.get("metro_lines", [])
        bus_data = transit_data.get("bus_routes", [])
        
        print(f"Base network loaded: {base_net.number_of_nodes()} nodes, {base_net.number_of_edges()} edges.")
        print(f"Loaded {len(metro_data)} metro lines and {len(bus_data)} bus routes.")

        visualize_transit_network(base_net, node_positions_data, node_type_data,
                                    metro_lines_data=metro_data, 
                                    bus_routes_data=bus_data,
                                    title="Greater Cairo Public Transit Network",
                                    output_path=output_viz_path)
        
        # Example: Visualize only metro lines
        visualize_transit_network(base_net, node_positions_data, node_type_data,
                                    metro_lines_data=metro_data, 
                                    bus_routes_data=None, # No bus routes
                                    title="Greater Cairo Metro Network",
                                    output_path=output_viz_path.replace(".png", "_metro_only.png"))
    else:
        print("Failed to load base network or transit data for visualization.")

