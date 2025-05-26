import sys
import os

# Add emergency module to path
EMERGENCY_MODULE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "emergency"))
if EMERGENCY_MODULE_PATH not in sys.path:
    sys.path.insert(0, EMERGENCY_MODULE_PATH)

from astar_emergency import get_emergency_graph, a_star_emergency_path
# For testing emergency_simulation and response_analysis, you might need to run the simulation
# or use pre-saved history, which is more complex for a simple unit test script.

# Define data paths relative to the transportation_system directory
TRANSPORTATION_SYSTEM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_BASE_PATH = os.path.join(TRANSPORTATION_SYSTEM_ROOT, "data")

def test_astar_emergency_basic():
    print("--- Testing Emergency: A* Emergency Path (Basic) ---")
    road_file = os.path.join(DATA_BASE_PATH, "road_data.json")
    facilities_file = os.path.join(DATA_BASE_PATH, "facilities.json")
    traffic_file = os.path.join(DATA_BASE_PATH, "traffic_data.json")

    graph = get_emergency_graph(road_file, facilities_file, traffic_file)
    if not graph:
        print("Test FAILED: Could not load graph for A* emergency.")
        return False

    nodes = list(graph.nodes())
    if len(nodes) < 2:
        print("Test SKIPPED: Not enough nodes for A* test.")
        return True
    
    # Try to find a facility as target if possible
    facility_nodes = [n for n, data in graph.nodes(data=True) if data.get("Type") == "Medical"]
    source = nodes[0]
    target = None
    if facility_nodes:
        target = facility_nodes[0]
        if source == target and len(nodes) > 1:
            source = nodes[1] if nodes[1] != target else (nodes[2] if len(nodes) > 2 and nodes[2] != target else None)
        elif source == target and len(facility_nodes) > 1:
            target = facility_nodes[1]
    
    if not target: # Fallback if no medical facility or source is the only medical facility
        target = nodes[1] if nodes[1] != source else (nodes[-1] if nodes[-1] != source else None)

    if source is None or target is None or source == target:
        print("Test SKIPPED: Could not find distinct source/target for A* test.")
        return True

    path, length = a_star_emergency_path(graph, source, target, weight_key="distance_km", emergency_priority_factor=0.8)
    if path and length is not None:
        print(f"Test PASSED: A* emergency path found from {source} to {target} with effective length {length:.2f}.")
        return True
    else:
        print(f"Test FAILED or NOTE: A* emergency path not found for {source} to {target}. This might be expected.")
        return False # Marking as False for now

if __name__ == "__main__":
    test_astar_emergency_basic()
    # Add calls to test emergency_simulation and response_analysis if they have simple testable units
    # or if you set up mock simulation history for response_analysis.
    print("Emergency module tests completed.")

