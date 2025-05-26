import json
import os
import sys

# Add module directories to sys.path to allow direct imports
# This assumes system_manager.py is in transportation_system/integration/
# and the script is run from the transportation_system directory or PYTHONPATH is set.
# For robustness, consider making these modules installable or using relative imports if structured as a package.
TRANSPORTATION_SYSTEM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATHS = [
    os.path.join(TRANSPORTATION_SYSTEM_ROOT, "infrastructure"),
    os.path.join(TRANSPORTATION_SYSTEM_ROOT, "traffic_flow"),
    os.path.join(TRANSPORTATION_SYSTEM_ROOT, "emergency"),
    os.path.join(TRANSPORTATION_SYSTEM_ROOT, "transit"),
]
for module_path in MODULE_PATHS:
    if module_path not in sys.path:
        sys.path.insert(0, module_path)

# Import functions from other modules
from kruskal_modified import get_infrastructure_graph, kruskal_mst_modified

from cost_analysis import analyze_potential_road_costs, analyze_mst_cost

from dijkstra_time_dependent import get_traffic_graph, dijkstra_time_dependent
from yen_alternate_routes import yen_k_shortest_paths # Assuming get_traffic_graph_for_yen is similar to get_traffic_graph
from congestion_analysis import calculate_congestion_levels, identify_bottlenecks, visualize_congestion_map
# traffic_simulation is more standalone for generating frames, might be called directly by dashboard

from astar_emergency import get_emergency_graph, a_star_emergency_path
# emergency_simulation and response_analysis might also be more direct calls or triggered by dashboard

from transit_optimization import get_transit_data, get_base_road_network_for_transit, optimize_bus_allocation_greedy, assess_new_metro_line_feasibility
from visualize_transit import visualize_transit_network # Assuming get_base_network_for_visualization is similar to get_base_road_network_for_transit
from improvement_analysis import analyze_demand_coverage, suggest_route_extensions_or_new_routes

DATA_BASE_PATH = os.path.join(TRANSPORTATION_SYSTEM_ROOT, "data")
OUTPUT_BASE_PATH = os.path.join(TRANSPORTATION_SYSTEM_ROOT, "output")
VISUALIZATIONS_OUTPUT_PATH = os.path.join(OUTPUT_BASE_PATH, "visualizations")
REPORTS_OUTPUT_PATH = os.path.join(OUTPUT_BASE_PATH, "reports") # New path for reports

# Ensure output directories exist
os.makedirs(VISUALIZATIONS_OUTPUT_PATH, exist_ok=True)
os.makedirs(REPORTS_OUTPUT_PATH, exist_ok=True)
os.makedirs(os.path.join(VISUALIZATIONS_OUTPUT_PATH, "simulation_frames"), exist_ok=True)
os.makedirs(os.path.join(VISUALIZATIONS_OUTPUT_PATH, "emergency_sim_frames"), exist_ok=True)

class SystemManager:
    def __init__(self):
        self.road_data_file = os.path.join(DATA_BASE_PATH, "road_data.json")
        self.facilities_data_file = os.path.join(DATA_BASE_PATH, "facilities.json")
        self.traffic_data_file = os.path.join(DATA_BASE_PATH, "traffic_data.json")
        self.transit_data_file = os.path.join(DATA_BASE_PATH, "transit_data.json")

        self.infra_graph = None
        self.traffic_graph = None
        self.emergency_graph = None
        self.transit_data = None
        self.base_road_network_for_transit = None
        self.base_network_for_transit_viz = None # For visualize_transit
        self.node_positions_for_transit_viz = None
        self.node_types_for_transit_viz = None
        
        self._load_all_graphs_and_data()

    def _load_all_graphs_and_data(self):
        print("SystemManager: Loading all graphs and data...")
        self.infra_graph = get_infrastructure_graph(self.road_data_file, self.facilities_data_file)
        self.traffic_graph = get_traffic_graph(self.road_data_file, self.facilities_data_file, self.traffic_data_file)
        self.emergency_graph = get_emergency_graph(self.road_data_file, self.facilities_data_file, self.traffic_data_file)
        self.transit_data = get_transit_data(self.transit_data_file)
        self.base_road_network_for_transit = get_base_road_network_for_transit(self.road_data_file, self.facilities_data_file)
        
        # For visualize_transit.py, it has its own loader: get_base_network_for_visualization
        # We need to call it to get the specific outputs it expects.
        from visualize_transit import get_base_network_for_visualization as transit_viz_loader
        self.base_network_for_transit_viz, self.node_positions_for_transit_viz, self.node_types_for_transit_viz = transit_viz_loader(self.road_data_file, self.facilities_data_file)
        
        if not all([self.infra_graph, self.traffic_graph, self.emergency_graph, self.transit_data, self.base_road_network_for_transit, self.base_network_for_transit_viz]):
            print("SystemManager: Error - One or more graphs/data failed to load.")
        else:
            print("SystemManager: All graphs and data loaded successfully.")

    # --- Infrastructure Module Functions ---
    def run_mst_analysis(self, weight_key="distance_km", consider_potential=False, critical_facilities=None, pop_threshold=0, pop_factor=0.1):
        if not self.infra_graph:
            return None, "Infrastructure graph not loaded."
        mst = kruskal_mst_modified(self.infra_graph, weight_key, consider_potential, critical_facilities, pop_threshold, pop_factor)
        if mst:
            analysis = analyze_mst_cost(mst, cost_attribute="cost_million_egp" if "cost" in weight_key else "distance_km")
            viz_path = os.path.join(VISUALIZATIONS_OUTPUT_PATH, f"mst_result_{weight_key}.png")
            visualize_network_graph(self.infra_graph, highlight_edges=list(mst.edges()), title=f"MST ({weight_key})", output_path=viz_path)
            analysis["visualization_path"] = viz_path
            return mst, analysis
        return None, "MST calculation failed."

    # --- Traffic Flow Module Functions ---
    def find_shortest_path(self, source, target, weight="distance_km", time_dependent=False, tod=None):
        if not self.traffic_graph:
            return None, None, "Traffic graph not loaded."
        path, length = dijkstra_time_dependent(self.traffic_graph, source, target, weight, time_dependent, tod)
        return path, length, None if path else "Path not found or error in calculation."

    def find_k_shortest_paths(self, source, target, k=3, weight="distance_km"):
        if not self.traffic_graph: # Yen might use a slightly different graph prep, ensure consistency
            return [], "Traffic graph not loaded for Yen."
        # Assuming get_traffic_graph_for_yen is similar or traffic_graph is suitable
        paths = yen_k_shortest_paths(self.traffic_graph, source, target, K=k, weight_key=weight)
        return paths, None if paths else "No paths found or error."

    def analyze_congestion(self, tod="morning_peak", threshold=0.85):
        if not self.traffic_graph:
            return None, None, "Traffic graph not loaded."
        congestion_levels = calculate_congestion_levels(self.traffic_graph, time_of_day=tod)
        bottlenecks = identify_bottlenecks(congestion_levels, threshold=threshold)
        viz_path = os.path.join(VISUALIZATIONS_OUTPUT_PATH, f"congestion_map_{tod}.png")
        visualize_congestion_map(self.traffic_graph, congestion_levels, tod, output_path=viz_path, threshold=threshold)
        return congestion_levels, bottlenecks, viz_path, None

    # --- Emergency Module Functions ---
    def find_emergency_route(self, source, target, weight="distance_km", time_dependent=False, tod=None, priority_factor=0.8):
        if not self.emergency_graph:
            return None, None, "Emergency graph not loaded."
        path, length = a_star_emergency_path(self.emergency_graph, source, target, weight, time_dependent, tod, priority_factor)
        return path, length, None if path else "Emergency path not found."

    # --- Transit Module Functions ---
    def run_bus_allocation_optimization(self, total_buses_override=None):
        if not self.transit_data or "bus_routes" not in self.transit_data or "public_transport_demand" not in self.transit_data:
            return None, "Transit data (bus routes or demand) missing."
        bus_routes = self.transit_data["bus_routes"]
        demand = self.transit_data["public_transport_demand"]
        current_total_buses = sum(r.get("Buses_Assigned",0) for r in bus_routes)
        total_buses = total_buses_override if total_buses_override is not None else current_total_buses
        
        allocations = optimize_bus_allocation_greedy(bus_routes, demand, total_buses)
        return allocations, None
    
    def assess_metro_feasibility(self, potential_line_stations):
        if not self.transit_data or not self.base_road_network_for_transit:
            return None, "Transit data or base road network missing."
        demand = self.transit_data["public_transport_demand"]
        existing_lines = self.transit_data["metro_lines"]
        assessment = assess_new_metro_line_feasibility(potential_line_stations, demand, existing_lines, self.base_road_network_for_transit)
        return assessment, None

    def get_transit_demand_coverage(self, optimized_bus_allocations=None):
        if not self.transit_data:
            return None, "Transit data missing."
        coverage = analyze_demand_coverage(self.transit_data, optimized_bus_allocations)
        return coverage, None

    def visualize_full_transit_network(self):
        if not self.base_network_for_transit_viz or not self.transit_data:
            return None, "Base network for transit viz or transit data missing."
        metro_data = self.transit_data.get("metro_lines", [])
        bus_data = self.transit_data.get("bus_routes", [])
        viz_path = os.path.join(VISUALIZATIONS_OUTPUT_PATH, "full_transit_map_managed.png")
        visualize_transit_network(self.base_network_for_transit_viz, 
                                  self.node_positions_for_transit_viz, 
                                  self.node_types_for_transit_viz,
                                  metro_lines_data=metro_data,
                                  bus_routes_data=bus_data,
                                  title="Managed Full Public Transit Network",
                                  output_path=viz_path)
        return viz_path, None

    def get_all_node_ids_names(self):
        """Returns a list of (ID, Name) for all nodes in the infra_graph for UI selectors."""
        if not self.infra_graph:
            return [], "Infrastructure graph not loaded."
        nodes_info = []
        for node_id, data in self.infra_graph.nodes(data=True):
            name = data.get("Name", f"Node {node_id}")
            nodes_info.append({"id": node_id, "name": name, "type": data.get("Type", "Unknown")})
        return sorted(nodes_info, key=lambda x: x["name"]), None

if __name__ == "__main__":
    manager = SystemManager()
    if not all([manager.infra_graph, manager.traffic_graph, manager.emergency_graph, manager.transit_data]):
        print("Exiting due to loading errors.")
        exit()

    print("\n--- Running System Manager Test Operations ---")

    # Test Infrastructure
    print("\n1. MST Analysis (Distance):")
    mst_dist, analysis_dist = manager.run_mst_analysis(weight_key="distance_km")
    if mst_dist:
        print(f"  MST (Distance) Edges: {len(mst_dist.edges())}, Total Distance: {analysis_dist['total_network_distance_km']:.2f} km")
        print(f"  Visualization: {analysis_dist['visualization_path']}")

    # Test Traffic Flow
    print("\n2. Shortest Path (Maadi to New Cairo - Morning Peak):")
    # Assuming node IDs '1' for Maadi, '4' for New Cairo from previous examples
    nodes_list, _ = manager.get_all_node_ids_names()
    node_1_id = next((n["id"] for n in nodes_list if "Maadi" in n["name"]), None) or "1"
    node_4_id = next((n["id"] for n in nodes_list if "New Cairo" in n["name"]), None) or "4"
    
    path, length, err = manager.find_shortest_path(node_1_id, node_4_id, time_dependent=True, tod="morning_peak")
    if path:
        print(f"  Path: {path}, Effective Length: {length:.2f}")
    else: print(f"  Error: {err}")

    print("\n3. Congestion Analysis (Evening Peak):")
    levels, bottlenecks, viz_path_cong, err_cong = manager.analyze_congestion(tod="evening_peak")
    if levels:
        print(f"  Identified {len(bottlenecks)} bottlenecks.")
        print(f"  Congestion map: {viz_path_cong}")
    else: print(f"  Error: {err_cong}")

    # Test Emergency
    print("\n4. Emergency Route (Nasr City to Qasr El Aini Hospital - Evening Peak):")
    # Assuming '2' for Nasr City, 'F9' for Qasr El Aini
    node_2_id = next((n["id"] for n in nodes_list if "Nasr City" in n["name"]), None) or "2"
    node_f9_id = next((n["id"] for n in nodes_list if "Qasr El Aini" in n["name"]), None) or "F9"

    em_path, em_length, em_err = manager.find_emergency_route(node_2_id, node_f9_id, time_dependent=True, tod="evening_peak", priority_factor=0.7)
    if em_path:
        print(f"  Emergency Path: {em_path}, Effective Length: {em_length:.2f}")
    else: print(f"  Error: {em_err}")

    # Test Transit
    print("\n5. Transit Demand Coverage:")
    coverage, err_cov = manager.get_transit_demand_coverage()
    if coverage:
        print(f"  Overall Direct Coverage: {coverage["percentage_any_direct_coverage"]}% of {coverage["total_daily_demand_passengers"]} passengers.")
    else: print(f"  Error: {err_cov}")

    print("\n6. Visualizing Full Transit Network:")
    transit_viz_p, transit_err_viz = manager.visualize_full_transit_network()
    if transit_viz_p:
        print(f"  Transit map saved to: {transit_viz_p}")
    else: print(f"  Error: {transit_err_viz}")

    print("\n--- System Manager Test Operations Completed ---")

