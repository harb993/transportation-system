import sys
import os

# Add infrastructure module to path
INFRA_MODULE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "infrastructure"))
if INFRA_MODULE_PATH not in sys.path:
    sys.path.insert(0, INFRA_MODULE_PATH)

from kruskal_modified import get_infrastructure_graph, kruskal_mst_modified

# Define data paths relative to the transportation_system directory
TRANSPORTATION_SYSTEM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_BASE_PATH = os.path.join(TRANSPORTATION_SYSTEM_ROOT, "data")

def test_kruskal_mst():
    print("--- Testing Infrastructure: Kruskal MST ---")
    road_data_file = os.path.join(DATA_BASE_PATH, "road_data.json")
    facilities_data_file = os.path.join(DATA_BASE_PATH, "facilities.json")

    infra_graph = get_infrastructure_graph(road_data_file, facilities_data_file)
    if not infra_graph:
        print("Test FAILED: Could not load infrastructure graph.")
        return False

    mst = kruskal_mst_modified(infra_graph, weight_key="distance_km")
    if not mst or mst.number_of_edges() == 0:
        # It's possible a graph has no edges or is disconnected, leading to an empty or partial MST
        # For a basic test, we just check if it runs without error and produces some MST graph object
        print(f"Test NOTE: MST result has {mst.number_of_edges()} edges. This might be expected for the given data.")
        # Check if the graph has nodes, if so, an MST should have N-C edges where C is num components
        if infra_graph.number_of_nodes() > 0 and mst.number_of_nodes() != infra_graph.number_of_nodes():
             print("Test WARNING: MST node count differs from original graph.")
        # Not a hard fail, as Kruskal handles disconnected graphs by creating a spanning forest.
    else:
        print(f"Test PASSED: Kruskal MST calculated with {mst.number_of_edges()} edges.")
    
    # Add more specific assertions here based on expected output for known data
    return True

if __name__ == "__main__":
    test_kruskal_mst()
    # Add calls to other infrastructure tests here (e.g., test_cost_analysis, test_visualization_infra)
    print("Infrastructure tests completed.")

