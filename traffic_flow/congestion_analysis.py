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

def get_full_traffic_graph(road_data_path, facilities_data_path, traffic_data_path):
    road_data = load_json_data(road_data_path)
    facilities_data = load_json_data(facilities_data_path)
    traffic_data = load_json_data(traffic_data_path)
    if not road_data or not traffic_data:
        return None
    graph = nx.DiGraph()
    if "nodes" in road_data:
        for node_info in road_data["nodes"]:
            graph.add_node(str(node_info["ID"]), **node_info)
    if facilities_data and "neighborhoods" in facilities_data:
        for facility_info in facilities_data["neighborhoods"]:
            fid = str(facility_info["ID"])
            if fid not in graph: graph.add_node(fid, **facility_info)
            else: graph.nodes[fid].update(facility_info)
    if "edges" in road_data:
        for edge_info in road_data["edges"]:
            u, v = str(edge_info["FromID"]), str(edge_info["ToID"])
            if not graph.has_node(u): graph.add_node(u, ID=u, Name=f"Node {u}")
            if not graph.has_node(v): graph.add_node(v, ID=v, Name=f"Node {v}")
            attrs = edge_info.copy()
            attrs["max_capacity_veh_hr"] = int(edge_info.get("Current_Capacity_vehicles_hour", edge_info.get("Estimated_Capacity_vehicles_hour", 1000)))
            graph.add_edge(u, v, **attrs)
    if traffic_data:
        for entry in traffic_data:
            u,v = str(entry["RoadID_From"]), str(entry["RoadID_To"])
            if graph.has_edge(u,v):
                for key, val in entry.items():
                    if key not in ["RoadID_From", "RoadID_To"]:
                        # Store traffic flow data directly on edge
                        graph[u][v][key.lower()] = int(val) 
    return graph

# --- Congestion Analysis ---
def calculate_congestion_levels(graph, time_of_day="morning_peak"):
    """
    Calculates congestion level (Volume/Capacity ratio) for each road segment.
    Args:
        graph (nx.DiGraph): The traffic graph.
        time_of_day (str): "morning_peak", "afternoon", "evening_peak", or "night".
    Returns:
        dict: A dictionary mapping edges (u,v) to their V/C ratio.
    """
    if graph is None:
        return {}

    congestion_data = {}
    traffic_col_map = {
        "morning_peak": "morning_peak_veh_h",
        "afternoon": "afternoon_veh_h",
        "evening_peak": "evening_peak_veh_h",
        "night": "night_veh_h"
    }
    flow_attribute = traffic_col_map.get(time_of_day)

    if not flow_attribute:
        print(f"Warning: Invalid time_of_day 	'{time_of_day}	'. Cannot calculate congestion.")
        return {}

    for u, v, data in graph.edges(data=True):
        volume = data.get(flow_attribute, 0)
        capacity = data.get("max_capacity_veh_hr", 0)
        
        if capacity > 0:
            vc_ratio = volume / capacity
        else:
            vc_ratio = float("inf") if volume > 0 else 0 # Infinite congestion if capacity is 0 but there is volume
        
        congestion_data[(u,v)] = {
            "volume": volume,
            "capacity": capacity,
            "vc_ratio": round(vc_ratio, 3)
        }
    return congestion_data

def identify_bottlenecks(congestion_levels, threshold=0.9):
    """Identifies bottleneck road segments based on V/C ratio threshold."""
    bottlenecks = []
    for edge, data in congestion_levels.items():
        if data["vc_ratio"] >= threshold:
            bottlenecks.append({
                "road_segment": edge,
                "from_node": edge[0],
                "to_node": edge[1],
                "volume": data["volume"],
                "capacity": data["capacity"],
                "vc_ratio": data["vc_ratio"]
            })
    return sorted(bottlenecks, key=lambda x: x["vc_ratio"], reverse=True)

# --- Visualization of Congestion ---
def visualize_congestion_map(graph, congestion_levels, time_of_day, 
                             output_path=None, threshold=0.9):
    if graph is None or not congestion_levels:
        print("Cannot visualize congestion: graph or congestion data missing.")
        return

    fig, ax = plt.subplots(figsize=(15, 12))
    pos = {node: (data.get("X_coordinate", random.random()), data.get("Y_coordinate", random.random())) 
           for node, data in graph.nodes(data=True)}

    edge_colors = []
    edge_widths = []
    
    # Determine color based on V/C ratio
    # Green (<0.5), Yellow (0.5-0.9), Red (>0.9), DarkRed (>1.2)
    for u, v, data in graph.edges(data=True):
        edge_id = (u,v)
        vc_ratio = congestion_levels.get(edge_id, {}).get("vc_ratio", 0)
        
        if vc_ratio >= 1.2:
            edge_colors.append("darkred")
            edge_widths.append(3.0)
        elif vc_ratio >= threshold: # Bottleneck threshold
            edge_colors.append("red")
            edge_widths.append(2.5)
        elif vc_ratio >= 0.5:
            edge_colors.append("yellow")
            edge_widths.append(1.5)
        else:
            edge_colors.append("green")
            edge_widths.append(1.0)

    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=30, node_color="skyblue", alpha=0.7)
    nx.draw_networkx_edges(graph, pos, ax=ax, edge_color=edge_colors, width=edge_widths, alpha=0.8)
    # nx.draw_networkx_labels(graph, pos, ax=ax, font_size=7)
    
    plt.title(f"Network Congestion Map ({time_of_day.replace("_", " ").title()})", fontsize=16)
    # Create a custom legend
    legend_elements = [
        plt.Line2D([0], [0], color="green", lw=2, label=f"Low Congestion (V/C < 0.5)"),
        plt.Line2D([0], [0], color="yellow", lw=2, label=f"Moderate Congestion (0.5 <= V/C < {threshold})"),
        plt.Line2D([0], [0], color="red", lw=2, label=f"High Congestion ({threshold} <= V/C < 1.2)"),
        plt.Line2D([0], [0], color="darkred", lw=2, label=f"Severe Congestion (V/C >= 1.2)")
    ]
    ax.legend(handles=legend_elements, loc="lower right", title="Congestion Level")
    plt.axis("off")

    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path)
        print(f"Congestion map saved to {output_path}")
    else:
        plt.show()
    plt.close(fig)

if __name__ == "__main__":
    print("Testing Congestion Analysis")
    base_data_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    output_viz_base = r"c:\Users\abdoo\Desktop\transportation_system\output\visualizations"
    
    road_file = base_data_path + r"\road_data.json"
    facilities_file = base_data_path + r"\facilities.json"
    traffic_file = base_data_path + r"\traffic_data.json"

    analysis_graph = get_full_traffic_graph(road_file, facilities_file, traffic_file)

    if analysis_graph:
        print(f"Graph for analysis loaded: {analysis_graph.number_of_nodes()} nodes, {analysis_graph.number_of_edges()} edges")
        
        times_to_analyze = ["morning_peak", "afternoon", "evening_peak"]
        bottleneck_threshold = 0.85

        for tod in times_to_analyze:
            print(f"\n--- Analyzing Congestion for: {tod.replace("_", " ").title()} ---")
            congestion = calculate_congestion_levels(analysis_graph, time_of_day=tod)
            
            if not congestion:
                print("No congestion data calculated.")
                continue

            bottlenecks = identify_bottlenecks(congestion, threshold=bottleneck_threshold)
            print(f"Identified {len(bottlenecks)} bottlenecks (V/C >= {bottleneck_threshold}):")
            for i, bn in enumerate(bottlenecks[:5]): # Print top 5
                print(f"  {i+1}. Road {bn["from_node"]}-{bn["to_node"]}: V/C = {bn["vc_ratio"]:.2f} (Vol: {bn["volume"]:.0f}, Cap: {bn["capacity"]:.0f})")
            
            viz_path = f"{output_viz_base}congestion_map_{tod}.png"
            visualize_congestion_map(analysis_graph, congestion, tod, output_path=viz_path, threshold=bottleneck_threshold)
    else:
        print("Failed to load graph for congestion analysis testing.")

