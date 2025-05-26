import json
import networkx as nx
import matplotlib.pyplot as plt
import folium
from folium import plugins
import os
import streamlit as st
from kruskal_modified import get_infrastructure_graph, kruskal_mst_modified

def log_debug(message, filepath="debug_log.txt"):
    """Helper function to log debug messages."""
    with open(filepath, "a") as f:
        f.write(message + "\n")

# --- Shared Data Loading ---
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

# --- Visualization Functions ---
def visualize_network_on_map(graph, mst=None):
    """Creates an interactive map visualization of the network."""
    # Find center coordinates for the map
    lats = []
    lons = []
    for node, data in graph.nodes(data=True):
        try:
            # Assuming coordinates are in latitude/longitude format
            lat = float(data.get("Y_coordinate", 0))
            lon = float(data.get("X_coordinate", 0))
            lats.append(lat)
            lons.append(lon)
        except (ValueError, TypeError):
            continue

    center_lat = sum(lats) / len(lats) if lats else 30.0444  # Default to Cairo coordinates
    center_lon = sum(lons) / len(lons) if lons else 31.2357

    # Create a map centered on the network
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # Add nodes
    for node, data in graph.nodes(data=True):
        try:
            lat = float(data.get("Y_coordinate", 0))
            lon = float(data.get("X_coordinate", 0))
            color = "green" if node.startswith("F") else "blue"
            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                popup=node,
                color=color,
                fill=True,
                fillOpacity=0.7
            ).add_to(m)
        except (ValueError, TypeError):
            continue

    # Draw edges
    if mst:
        # Draw MST edges
        for u, v, data in mst.edges(data=True):
            try:
                u_lat = float(graph.nodes[u]["Y_coordinate"])
                u_lon = float(graph.nodes[u]["X_coordinate"])
                v_lat = float(graph.nodes[v]["Y_coordinate"])
                v_lon = float(graph.nodes[v]["X_coordinate"])
                
                color = "red" if data.get("type") == "existing_road" else "blue"
                weight = 4
                
                folium.PolyLine(
                    locations=[[u_lat, u_lon], [v_lat, v_lon]],
                    weight=weight,
                    color=color,
                    opacity=0.8,
                    popup=f"Road: {u} to {v}"
                ).add_to(m)
            except (ValueError, TypeError, KeyError):
                continue

        # Draw non-MST edges as gray dashed lines
        for u, v in graph.edges():
            if not mst.has_edge(u, v):
                try:
                    u_lat = float(graph.nodes[u]["Y_coordinate"])
                    u_lon = float(graph.nodes[u]["X_coordinate"])
                    v_lat = float(graph.nodes[v]["Y_coordinate"])
                    v_lon = float(graph.nodes[v]["X_coordinate"])
                    
                    folium.PolyLine(
                        locations=[[u_lat, u_lon], [v_lat, v_lon]],
                        weight=2,
                        color='gray',
                        opacity=0.4,
                        dash_array='5, 5'
                    ).add_to(m)
                except (ValueError, TypeError, KeyError):
                    continue

    # Add a fullscreen button
    plugins.Fullscreen().add_to(m)
    
    return m

# --- Main Function ---
def main():
    """Main function to load data, compute MSTs, and visualize the network."""
    debug_log = "debug_log.txt"
    if os.path.exists(debug_log):
        os.remove(debug_log)
    
    log_debug("Script started")
    # Setup paths
    base_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    # Output directory in infrastructure/out
    output_dir = r"C:\Users\abdoo\Desktop\transportation_system\infrastructure\out"
    road_data_file = os.path.join(base_path, "road_data.json")
    facilities_data_file = os.path.join(base_path, "facilities.json")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    log_debug(f"Checking road data file: {road_data_file}")
    log_debug(f"Checking facilities data file: {facilities_data_file}")
    if not os.path.exists(road_data_file):
        log_debug(f"Error: Road data file not found at {road_data_file}")
        return
    if not os.path.exists(facilities_data_file):
        log_debug(f"Error: Facilities data file not found at {facilities_data_file}")
        return

    # Load and construct graph
    infra_graph = get_infrastructure_graph(road_data_file, facilities_data_file)

    if infra_graph:
        log_debug("\nLoaded infrastructure graph successfully")
        log_debug(f"Graph: {infra_graph.number_of_nodes()} nodes, {infra_graph.number_of_edges()} edges")
        
        # Debug: Print edge types in the initial graph
        existing_count = sum(1 for _, _, d in infra_graph.edges(data=True) if d.get("type") == "existing_road")
        potential_count = sum(1 for _, _, d in infra_graph.edges(data=True) if d.get("type") == "potential_road")
        log_debug("\nInitial graph edge composition:")
        log_debug(f"- Existing roads: {existing_count}")
        log_debug(f"- Potential roads: {potential_count}")

        # Find isolated nodes
        isolated_nodes = [node for node in infra_graph.nodes() if infra_graph.degree(node) == 0]
        if isolated_nodes:
            log_debug("\nFound isolated nodes:")
            for node in isolated_nodes:
                log_debug(f"  - {node}")

        # Generate optimal MST considering both existing and potential roads
        log_debug("\nGenerating optimal MST...")
        mst = kruskal_mst_modified(infra_graph,
                                  weight_key="distance_km",
                                  consider_potential_roads=True,
                                  critical_facility_ids=["F3", "F4", "F5", "F6", "F9", "F10"])
        
        # Debug: Print edge composition of optimal MST
        if mst:
            existing_count = sum(1 for _, _, d in mst.edges(data=True) if d.get("type") == "existing_road")
            potential_count = sum(1 for _, _, d in mst.edges(data=True) if d.get("type") == "potential_road")
            log_debug("\nOptimal MST edge composition:")
            log_debug(f"- Existing roads: {existing_count}")
            log_debug(f"- Potential roads: {potential_count}")

        try:
            # Visualize optimal MST on map
            m = visualize_network_on_map(infra_graph, mst)
            
            # Save the visualization
            output_path = os.path.join(output_dir, "optimal_mst_map.html")
            m.save(output_path)
            log_debug(f"\nOptimal MST map visualization saved to: {output_path}")

        except Exception as e:
            log_debug(f"\nError during visualization: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        log_debug("Failed to load infrastructure graph for visualization.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_debug(f"Unexpected error in main: {str(e)}")
        import traceback
        traceback.print_exc()