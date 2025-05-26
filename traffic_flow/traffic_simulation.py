import json
import networkx as nx
import random
import matplotlib.pyplot as plt
import numpy as np

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

def get_base_traffic_graph(road_data_path, facilities_data_path, traffic_data_path):
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
            attrs["current_vehicles"] = 0
            attrs["max_capacity"] = int(edge_info.get("Current_Capacity_vehicles_hour", edge_info.get("Estimated_Capacity_vehicles_hour", 1000)))
            graph.add_edge(u, v, **attrs)
    if traffic_data:
        for entry in traffic_data:
            u,v = str(entry["RoadID_From"]), str(entry["RoadID_To"])
            if graph.has_edge(u,v):
                for key, val in entry.items():
                    if key not in ["RoadID_From", "RoadID_To"]:
                        graph[u][v][key.lower()] = int(val) # e.g. morning_peak_veh_h
    return graph

# --- Traffic Simulation (Conceptual Agent-Based) ---
class TrafficSimulator:
    def __init__(self, graph, num_vehicles=1000, simulation_steps=100):
        self.graph = graph.copy() # Work on a copy
        self.num_vehicles = num_vehicles
        self.simulation_steps = simulation_steps
        self.vehicles = [] # List of vehicle agents
        self.initialize_vehicles()
        self.history = [] # To store state at each step for visualization

    def initialize_vehicles(self):
        nodes = list(self.graph.nodes())
        if not nodes: return
        for i in range(self.num_vehicles):
            start_node = random.choice(nodes)
            # Assign a random destination, ensure it is not the start_node
            possible_destinations = [n for n in nodes if n != start_node]
            if not possible_destinations: continue # Should not happen in a connected graph with >1 nodes
            destination_node = random.choice(possible_destinations)
            self.vehicles.append({
                "id": i,
                "current_node": start_node,
                "destination_node": destination_node,
                "path": None, # Will be calculated using Dijkstra
                "path_index": 0,
                "status": "idle" # idle, moving, arrived
            })

    def _get_path(self, source, target):
        try:
            # Simple Dijkstra for path, not considering dynamic congestion for agent path choice here
            path = nx.dijkstra_path(self.graph, source, target, weight="Distance_km")
            return path
        except nx.NetworkXNoPath:
            return None
        except KeyError: # If Distance_km is missing
            try: # Fallback to unweighted path
                return nx.shortest_path(self.graph, source, target)
            except nx.NetworkXNoPath:
                return None

    def step(self, current_time_of_day="afternoon"):
        # Reset current vehicle counts on edges for this step
        for u, v, data in self.graph.edges(data=True):
            data["current_vehicles_on_edge"] = 0

        for vehicle in self.vehicles:
            if vehicle["status"] == "arrived":
                continue

            if vehicle["status"] == "idle" or vehicle["path"] is None:
                vehicle["path"] = self._get_path(vehicle["current_node"], vehicle["destination_node"])
                vehicle["path_index"] = 0
                if vehicle["path"]:
                    vehicle["status"] = "moving"
                else:
                    # No path, vehicle remains idle or could be removed/reassigned
                    vehicle["status"] = "stuck"
                    continue
            
            if vehicle["status"] == "moving":
                if vehicle["path_index"] < len(vehicle["path"]) - 1:
                    current_loc = vehicle["path"][vehicle["path_index"]]
                    next_loc = vehicle["path"][vehicle["path_index"] + 1]
                    
                    # Simulate movement: check edge capacity (simplified)
                    edge_data = self.graph.get_edge_data(current_loc, next_loc)
                    if edge_data:
                        # Use time-of-day specific capacity if available, else base capacity
                        # This is a conceptual capacity, not flow rate
                        capacity_key = f"{current_time_of_day}_veh_h" # e.g. afternoon_veh_h
                        edge_capacity = edge_data.get(capacity_key, edge_data.get("max_capacity", 100))
                        current_on_edge = edge_data.get("current_vehicles_on_edge", 0)
                        
                        # Simple rule: move if edge is not "full" (e.g. < 90% of hourly rate as momentary capacity)
                        # This is highly abstract for a discrete step simulation.
                        if current_on_edge < edge_capacity * 0.1: # Assume 0.1 of hourly rate per step
                            vehicle["current_node"] = next_loc
                            vehicle["path_index"] += 1
                            edge_data["current_vehicles_on_edge"] = current_on_edge + 1
                        # else: vehicle waits (stays at current_loc, effectively congested)
                else:
                    vehicle["status"] = "arrived"
        
        # Record history (simplified: just count vehicles on edges)
        edge_load = {(u,v): data.get("current_vehicles_on_edge", 0) for u,v,data in self.graph.edges(data=True)}
        self.history.append(edge_load)

    def run_simulation(self):
        time_of_day_cycle = ["morning_peak", "afternoon", "evening_peak", "night"] * (self.simulation_steps // 4 + 1)
        for i in range(self.simulation_steps):
            current_tod = time_of_day_cycle[i % len(time_of_day_cycle)]
            self.step(current_tod)
            print(f"Simulation Step {i+1}/{self.simulation_steps} (Time: {current_tod}) completed.")
            if all(v["status"] in ["arrived", "stuck"] for v in self.vehicles):
                print("All vehicles arrived or stuck. Ending simulation early.")
                break
        return self.history

# --- Visualization of Simulation (Conceptual) ---
def visualize_simulation_step(graph, edge_loads, step_num, output_dir=r"c:\Users\abdoo\Desktop\transportation_system\output\visualizations"):
    fig, ax = plt.subplots(figsize=(12,10))
    pos = {node: (data.get("X_coordinate", random.random()), data.get("Y_coordinate", random.random())) 
           for node, data in graph.nodes(data=True)}
    
    edge_colors = []
    edge_widths = []
    max_load = max(max(edge_loads.values()) if edge_loads else [1], 1) # Avoid division by zero
    
    for u,v in graph.edges():
        load = edge_loads.get((u,v), 0)
        color_intensity = min(1.0, load / (max_load * 0.5 + 1e-6)) # Normalize for color
        edge_colors.append(plt.cm.Reds(color_intensity))
        edge_widths.append(1 + (load / (max_load + 1e-6)) * 4) # Width based on load

    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=50, node_color="lightblue")
    nx.draw_networkx_edges(graph, pos, ax=ax, edge_color=edge_colors, width=edge_widths)
    # nx.draw_networkx_labels(graph, pos, ax=ax, font_size=8)
    plt.title(f"Traffic Simulation - Step {step_num}")
    plt.axis("off")
    
    import os
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f"{output_dir}sim_step_{step_num:03d}.png")
    plt.close(fig)

if __name__ == "__main__":
    print("Testing Traffic Simulation (Conceptual)")
    base_data_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    road_file = base_data_path + r"\road_data.json"
    facilities_file = base_data_path + r"\facilities.json"
    traffic_file = base_data_path + r"\traffic_data.json"
    sim_output_dir = r"c:\Users\abdoo\Desktop\transportation_system\output\visualizations\simulation_frames"

    sim_graph = get_base_traffic_graph(road_file, facilities_file, traffic_file)

    if sim_graph:
        print(f"Graph for simulation loaded: {sim_graph.number_of_nodes()} nodes, {sim_graph.number_of_edges()} edges")
        simulator = TrafficSimulator(sim_graph, num_vehicles=200, simulation_steps=50)
        simulation_history = simulator.run_simulation()
        
        print(f"Simulation finished. Visualizing {len(simulation_history)} steps...")
        for i, edge_loads_at_step in enumerate(simulation_history):
            visualize_simulation_step(sim_graph, edge_loads_at_step, i, output_dir=sim_output_dir)
        print(f"Simulation frames saved to {sim_output_dir}")
        print("To create a video from frames (requires ffmpeg):")
        print(f"ffmpeg -r 10 -i {sim_output_dir}sim_step_%03d.png -c:v libx264 -vf fps=25 -pix_fmt yuv420p {sim_output_dir}../traffic_simulation.mp4")

    else:
        print("Failed to load graph for simulation testing.")

