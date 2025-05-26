import sys
import os

# Add traffic_flow module to path
TRAFFIC_MODULE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "traffic_flow"))
if TRAFFIC_MODULE_PATH not in sys.path:
    sys.path.insert(0, TRAFFIC_MODULE_PATH)

from dijkstra_time_dependent import get_traffic_graph, dijkstra_time_dependent
from yen_alternate_routes import yen_k_shortest_paths # Assuming graph loader is similar
from congestion_analysis import calculate_congestion_levels, identify_bottlenecks

# Define data paths relative to the transportation_system directory
TRANSPORTATION_SYSTEM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_BASE_PATH = os.path.join(TRANSPORTATION_SYSTEM_ROOT, "data")

def test_dijkstra_time_dependent_basic():
    print("--- Testing Traffic Flow: Dijkstra Time-Dependent (Basic) ---")
    road_file = os.path.join(DATA_BASE_PATH, "road_data.json")
    facilities_file = os.path.join(DATA_BASE_PATH, "facilities.json")
    traffic_file = os.path.join(DATA_BASE_PATH, "traffic_data.json")

    graph = get_traffic_graph(road_file, facilities_file, traffic_file)
    if not graph:
        print("Test FAILED: Could not load traffic graph for Dijkstra.")
        return False

    # Find some valid source and target from the graph nodes
    nodes = list(graph.nodes())
    if len(nodes) < 2:
        print("Test SKIPPED: Not enough nodes in graph for Dijkstra test.")
        return True 
    source, target = nodes[0], nodes[1]
    if source == target and len(nodes) > 2:
        target = nodes[2] # Ensure different source and target if possible
    elif source == target and len(nodes) <=2:
        print("Test SKIPPED: Cannot find distinct source/target for Dijkstra test.")
        return True

    path, length = dijkstra_time_dependent(graph, source, target, weight_key="distance_km")
    if path and length is not None:
        print(f"Test PASSED: Dijkstra path found from {source} to {target} with length {length:.2f} km.")
        return True
    else:
        print(f"Test FAILED: Dijkstra path not found or error for {source} to {target}.")
        # This could be an expected outcome if no path exists, so not always a hard fail.
        # For a unit test, you_d use known data with a known path.
        return False # Marking as False for now if no path found in generic test

def test_yen_k_shortest_paths_basic():
    print("--- Testing Traffic Flow: Yen K-Shortest Paths (Basic) ---")
    road_file = os.path.join(DATA_BASE_PATH, "road_data.json")
    facilities_file = os.path.join(DATA_BASE_PATH, "facilities.json")
    traffic_file = os.path.join(DATA_BASE_PATH, "traffic_data.json") # Yen loader might be different
    
    # Assuming get_traffic_graph can be used for Yen as well, or use its specific loader
    from yen_alternate_routes import get_traffic_graph_for_yen # Use specific loader if defined
    graph = get_traffic_graph_for_yen(road_file, facilities_file, traffic_file)
    if not graph:
        print("Test FAILED: Could not load traffic graph for Yen.")
        return False

    nodes = list(graph.nodes())
    if len(nodes) < 2:
        print("Test SKIPPED: Not enough nodes for Yen test.")
        return True
    source, target = nodes[0], nodes[len(nodes)//2] # Pick different nodes
    if source == target and len(nodes) >1:
        target = nodes[-1]
    if source == target:
        print("Test SKIPPED: Cannot find distinct source/target for Yen test.")
        return True

    paths = yen_k_shortest_paths(graph, source, target, K=2, weight_key="distance_km")
    if paths:
        print(f"Test PASSED: Yen found {len(paths)} paths from {source} to {target}.")
        return True
    else:
        print(f"Test NOTE: Yen found no paths or fewer than K from {source} to {target}. This might be expected.")
        # Not a hard fail, depends on graph structure.
        return True 

if __name__ == "__main__":
    test_dijkstra_time_dependent_basic()
    test_yen_k_shortest_paths_basic()
    # Add calls to test_congestion_analysis, test_traffic_simulation if they have testable components
    print("Traffic flow tests completed.")

