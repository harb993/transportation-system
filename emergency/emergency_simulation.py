import json
import networkx as nx
import random
import matplotlib.pyplot as plt

# Assuming astar_emergency.py is in the same directory or accessible via sys.path
from astar_emergency import get_emergency_graph, a_star_emergency_path 

# --- Emergency Simulation (Conceptual) ---
class EmergencySimulator:
    def __init__(self, graph, num_incidents=5, simulation_steps=50):
        self.graph = graph.copy()
        self.num_incidents = num_incidents
        self.simulation_steps = simulation_steps
        self.incidents = [] # List of active incidents
        self.emergency_vehicles = [] # List of emergency vehicles
        self.history = [] # To store state for visualization
        self.medical_facilities = [node for node, data in self.graph.nodes(data=True) if data.get("Type") == "Medical"]
        self.initialize_vehicles(num_vehicles=num_incidents) # Assume one vehicle per potential incident initially

    def initialize_vehicles(self, num_vehicles=5):
        # For simplicity, assume vehicles start at or near medical facilities or central dispatch points
        # Here, let them start at random medical facilities if available, else random nodes
        start_nodes = self.medical_facilities if self.medical_facilities else list(self.graph.nodes())
        if not start_nodes: return

        for i in range(num_vehicles):
            self.emergency_vehicles.append({
                "id": f"EV{i}",
                "current_node": random.choice(start_nodes),
                "status": "available", # available, enroute_to_incident, enroute_to_facility, at_facility
                "incident_target": None, # Node of the incident
                "facility_target": None, # Node of the medical facility
                "path": None,
                "path_index": 0,
                "payload": False # True if carrying patient
            })

    def generate_incident(self, step):
        # Generate a new incident periodically or based on some probability
        if random.random() < 0.1 and len(self.incidents) < self.num_incidents * 2: # Limit active incidents
            incident_node = random.choice(list(self.graph.nodes()))
            # Ensure incident is not at a medical facility itself
            if incident_node in self.medical_facilities and len(list(self.graph.nodes())) > len(self.medical_facilities):
                possible_incident_nodes = [n for n in list(self.graph.nodes()) if n not in self.medical_facilities]
                if possible_incident_nodes:
                    incident_node = random.choice(possible_incident_nodes)
                else: return # No suitable node for incident
            
            new_incident = {
                "id": f"INC{step}_{len(self.incidents)}",
                "location": incident_node,
                "time_reported": step,
                "status": "pending_dispatch", # pending_dispatch, vehicle_assigned, resolved
                "assigned_vehicle": None
            }
            self.incidents.append(new_incident)
            print(f"Step {step}: New incident {new_incident["id"]} at {self.graph.nodes[incident_node].get("Name", incident_node)}")

    def dispatch_vehicle(self, incident, current_time_of_day):
        available_vehicles = [v for v in self.emergency_vehicles if v["status"] == "available"]
        if not available_vehicles: return False

        # Find closest available vehicle (simplistic: by current node distance to incident)
        # A more complex dispatch would consider travel time using A*
        best_vehicle = None
        shortest_path_to_incident = None
        min_len_to_incident = float("inf")

        for vehicle in available_vehicles:
            path, length = a_star_emergency_path(self.graph, vehicle["current_node"], incident["location"],
                                                 time_dependent=True, time_of_day=current_time_of_day,
                                                 emergency_priority_factor=0.8)
            if path and length < min_len_to_incident:
                min_len_to_incident = length
                shortest_path_to_incident = path
                best_vehicle = vehicle
        
        if best_vehicle and shortest_path_to_incident:
            best_vehicle["status"] = "enroute_to_incident"
            best_vehicle["incident_target"] = incident["location"]
            best_vehicle["path"] = shortest_path_to_incident
            best_vehicle["path_index"] = 0
            incident["status"] = "vehicle_assigned"
            incident["assigned_vehicle"] = best_vehicle["id"]
            print(f"Dispatch: Vehicle {best_vehicle["id"]} assigned to incident {incident["id"]}.")
            return True
        return False

    def step_simulation(self, step_num, current_time_of_day):
        self.generate_incident(step_num)

        # Dispatch to pending incidents
        for incident in self.incidents:
            if incident["status"] == "pending_dispatch":
                self.dispatch_vehicle(incident, current_time_of_day)

        # Move vehicles
        for vehicle in self.emergency_vehicles:
            if vehicle["status"] == "available" or vehicle["path"] is None:
                continue

            if vehicle["path_index"] < len(vehicle["path"]) - 1:
                # Simplified movement: assume one segment per step for emergency vehicles
                vehicle["current_node"] = vehicle["path"][vehicle["path_index"] + 1]
                vehicle["path_index"] += 1
            else: # Reached end of current path segment
                if vehicle["status"] == "enroute_to_incident":
                    vehicle["current_node"] = vehicle["incident_target"]
                    vehicle["payload"] = True # Picked up patient
                    # Find path to closest medical facility
                    closest_facility_node = None
                    min_len_to_facility = float("inf")
                    path_to_facility = None

                    if not self.medical_facilities:
                        print(f"Warning: No medical facilities defined for vehicle {vehicle["id"]}.")
                        vehicle["status"] = "available" # Or stuck
                        vehicle["payload"] = False
                        continue
                        
                    for facility_node in self.medical_facilities:
                        path, length = a_star_emergency_path(self.graph, vehicle["current_node"], facility_node,
                                                             time_dependent=True, time_of_day=current_time_of_day,
                                                             emergency_priority_factor=0.7) # Higher priority with payload
                        if path and length < min_len_to_facility:
                            min_len_to_facility = length
                            path_to_facility = path
                            closest_facility_node = facility_node
                    
                    if path_to_facility:
                        vehicle["status"] = "enroute_to_facility"
                        vehicle["facility_target"] = closest_facility_node
                        vehicle["path"] = path_to_facility
                        vehicle["path_index"] = 0
                        # Mark incident as resolved (or in transit)
                        for inc in self.incidents:
                            if inc["assigned_vehicle"] == vehicle["id"] and inc["status"] == "vehicle_assigned":
                                inc["status"] = "resolved" # Or enroute_hospital
                                print(f"Incident {inc["id"]} patient picked up by {vehicle["id"]}, enroute to {self.graph.nodes[closest_facility_node].get("Name", closest_facility_node)}.")
                                break
                    else:
                        print(f"Vehicle {vehicle["id"]} could not find path to facility from {vehicle["current_node"]}.")
                        vehicle["status"] = "available" # Or stuck
                        vehicle["payload"] = False
                
                elif vehicle["status"] == "enroute_to_facility":
                    vehicle["current_node"] = vehicle["facility_target"]
                    vehicle["status"] = "at_facility" # Could become available after a delay
                    vehicle["payload"] = False
                    print(f"Vehicle {vehicle["id"]} arrived at facility {self.graph.nodes[vehicle["facility_target"]].get("Name", vehicle["facility_target"])}.")
                    # Make vehicle available again after a short delay (e.g. next step)
                    # For now, make available immediately for simplicity in this step-based sim
                    vehicle["status"] = "available"
                    vehicle["path"] = None
                    vehicle["path_index"] = 0
        
        # Record state for history
        current_state = {
            "step": step_num,
            "time_of_day": current_time_of_day,
            "vehicles": [{k:v for k,v in veh.items() if k != "path"} for veh in self.emergency_vehicles],
            "incidents": [{k:v for k,v in inc.items()} for inc in self.incidents if inc["status"] != "resolved"]
        }
        self.history.append(current_state)

    def run(self):
        time_of_day_cycle = ["morning_peak", "afternoon", "evening_peak", "night"] * (self.simulation_steps // 4 + 1)
        for i in range(self.simulation_steps):
            current_tod = time_of_day_cycle[i % len(time_of_day_cycle)]
            self.step_simulation(i, current_tod)
            print(f"Emergency Sim Step {i+1}/{self.simulation_steps} (Time: {current_tod}) completed.")
            # Check for termination condition (e.g., all incidents resolved and no new ones for a while)
            if not [inc for inc in self.incidents if inc["status"] != "resolved"] and i > self.num_incidents * 2:
                 if random.random() > 0.5: # Chance to stop if quiet
                    print("Simulation quiet, ending early.")
                    break
        return self.history

# --- Visualization of Emergency Simulation (Conceptual) ---
def visualize_emergency_step(graph, sim_state, output_dir=r"c:\Users\abdoo\Desktop\transportation_system\output\visualizations\emergency_sim_frames"):
    fig, ax = plt.subplots(figsize=(14,11))
    pos = {node: (data.get("X_coordinate", random.random()), data.get("Y_coordinate", random.random())) 
           for node, data in graph.nodes(data=True)}
    
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=30, node_color="lightgray", alpha=0.5)
    nx.draw_networkx_edges(graph, pos, ax=ax, edge_color="gray", alpha=0.3)
    # nx.draw_networkx_labels(graph, pos, ax=ax, font_size=7, alpha=0.7)

    # Draw incidents
    incident_nodes = [inc["location"] for inc in sim_state["incidents"] if inc["status"] != "resolved"]
    if incident_nodes:
        nx.draw_networkx_nodes(graph, pos, nodelist=incident_nodes, ax=ax, node_size=100, node_color="red", node_shape="X", label="Incidents")

    # Draw medical facilities
    facility_nodes = [node for node, data in graph.nodes(data=True) if data.get("Type") == "Medical"]
    if facility_nodes:
        nx.draw_networkx_nodes(graph, pos, nodelist=facility_nodes, ax=ax, node_size=120, node_color="green", node_shape="s", label="Hospitals")

    # Draw vehicles and their paths
    for veh in sim_state["vehicles"]:
        node_color = "blue"
        if veh["status"] == "enroute_to_incident": node_color = "orange"
        elif veh["status"] == "enroute_to_facility": node_color = "purple"
        elif veh["status"] == "at_facility": node_color = "darkgreen"
        
        nx.draw_networkx_nodes(graph, pos, nodelist=[veh["current_node"]], ax=ax, node_size=80, node_color=node_color, node_shape="^")
        # Draw vehicle path if it exists (from original astar_emergency.py or current vehicle path)
        # This part needs vehicle to store its current full path for visualization
        # The current `vehicle["path"]` is the one it is following.
        if veh.get("path") and len(veh["path"]) > 1:
            path_edges = list(zip(veh["path"][:-1], veh["path"][1:]))
            nx.draw_networkx_edges(graph, pos, edgelist=path_edges, ax=ax, edge_color=node_color, width=2.0, style="dashed")

    plt.title(f"Emergency Simulation - Step {sim_state["step"]} ({sim_state["time_of_day"]})")
    # Create a simple legend
    legend_elements = [
        plt.Line2D([0], [0], marker="X", color="w", label="Incident", markerfacecolor="red", markersize=10),
        plt.Line2D([0], [0], marker="s", color="w", label="Hospital", markerfacecolor="green", markersize=10),
        plt.Line2D([0], [0], marker="^", color="w", label="EV (Available)", markerfacecolor="blue", markersize=8),
        plt.Line2D([0], [0], marker="^", color="w", label="EV (To Incident)", markerfacecolor="orange", markersize=8),
        plt.Line2D([0], [0], marker="^", color="w", label="EV (To Hospital)", markerfacecolor="purple", markersize=8),
    ]
    ax.legend(handles=legend_elements, loc="upper right")
    plt.axis("off")
    
    import os
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f"{output_dir}emergency_sim_step_{sim_state["step"]:03d}.png")
    plt.close(fig)

if __name__ == "__main__":
    print("Testing Emergency Simulation (Conceptual)")
    base_data_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    sim_output_dir_em = r"c:\Users\abdoo\Desktop\transportation_system\output\visualizations\emergency_sim_frames"

    road_file = base_data_path + r"\road_data.json"
    facilities_file = base_data_path + r"\facilities.json"
    traffic_file = base_data_path + r"\traffic_data.json"

    em_sim_graph = get_emergency_graph(road_file, facilities_file, traffic_file)

    if em_sim_graph:
        print(f"Graph for emergency sim loaded: {em_sim_graph.number_of_nodes()} nodes, {em_sim_graph.number_of_edges()} edges")
        if not [n for n,d in em_sim_graph.nodes(data=True) if d.get("Type") == "Medical"]:
            print("Warning: No medical facilities found in graph. Simulation might not be meaningful.")
            # Add a dummy medical facility for testing if none exist
            # For real use, ensure data is correct.
            if em_sim_graph.nodes(): # if graph has nodes
                dummy_facility_node = list(em_sim_graph.nodes())[0]
                em_sim_graph.nodes[dummy_facility_node]["Type"] = "Medical"
                print(f"Added dummy Medical type to node {dummy_facility_node} for simulation testing.")
            else:
                print("Graph has no nodes, cannot run simulation.")
                exit()

        em_simulator = EmergencySimulator(em_sim_graph, num_incidents=3, simulation_steps=30)
        em_history = em_simulator.run()
        
        print(f"Emergency simulation finished. Visualizing {len(em_history)} steps...")
        for i, state_at_step in enumerate(em_history):
            visualize_emergency_step(em_sim_graph, state_at_step, output_dir=sim_output_dir_em)
        print(f"Emergency simulation frames saved to {sim_output_dir_em}")
        print("To create a video (requires ffmpeg):")
        print(f"ffmpeg -r 5 -i {sim_output_dir_em}emergency_sim_step_%03d.png -c:v libx264 -vf fps=10 -pix_fmt yuv420p {sim_output_dir_em}../emergency_simulation.mp4")
    else:
        print("Failed to load graph for emergency simulation testing.")

