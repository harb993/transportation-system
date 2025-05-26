import sys
import os

# Add integration module to path
INTEGRATION_MODULE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "integration"))
if INTEGRATION_MODULE_PATH not in sys.path:
    sys.path.insert(0, INTEGRATION_MODULE_PATH)

# Add other module paths as SystemManager imports them
TRANSPORTATION_SYSTEM_ROOT_FOR_TEST = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATHS_FOR_TEST = [
    os.path.join(TRANSPORTATION_SYSTEM_ROOT_FOR_TEST, "infrastructure"),
    os.path.join(TRANSPORTATION_SYSTEM_ROOT_FOR_TEST, "traffic_flow"),
    os.path.join(TRANSPORTATION_SYSTEM_ROOT_FOR_TEST, "emergency"),
    os.path.join(TRANSPORTATION_SYSTEM_ROOT_FOR_TEST, "transit"),
]
for module_path in MODULE_PATHS_FOR_TEST:
    if module_path not in sys.path:
        sys.path.insert(0, module_path)

from system_manager import SystemManager

# Define data paths relative to the transportation_system directory
# TRANSPORTATION_SYSTEM_ROOT is already defined by system_manager when it runs
# DATA_BASE_PATH = os.path.join(TRANSPORTATION_SYSTEM_ROOT, "data")

def test_system_manager_initialization():
    print("--- Testing Integration: SystemManager Initialization ---")
    manager = SystemManager()
    if manager.infra_graph and manager.traffic_graph and manager.emergency_graph and manager.transit_data:
        print("Test PASSED: SystemManager initialized and loaded all graphs/data successfully.")
        # Verify some basic graph properties if possible
        if manager.infra_graph.number_of_nodes() > 0:
            print(f"  Infra graph has {manager.infra_graph.number_of_nodes()} nodes.")
        else:
            print("  Infra graph has 0 nodes - check data if this is unexpected.")
        return True
    else:
        print("Test FAILED: SystemManager failed to initialize or load all data.")
        return False

def test_system_manager_sample_operations():
    print("--- Testing Integration: SystemManager Sample Operations ---")
    manager = SystemManager()
    if not (manager.infra_graph and manager.traffic_graph and manager.emergency_graph and manager.transit_data):
        print("Test SKIPPED: SystemManager did not initialize correctly.")
        return False

    all_passed = True

    # Test a simple operation from each module via manager
    print("  Testing MST Analysis via Manager...")
    mst, analysis = manager.run_mst_analysis(weight_key="distance_km")
    if mst and analysis and "visualization_path" in analysis:
        print(f"    MST Analysis PASSED. Viz: {analysis["visualization_path"]}")
    else:
        print(f"    MST Analysis FAILED or error: {analysis}")
        all_passed = False

    print("  Testing Shortest Path via Manager...")
    nodes_list, _ = manager.get_all_node_ids_names()
    if len(nodes_list) < 2:
        print("    Shortest Path SKIPPED: Not enough nodes for test.")
    else:
        source_id = nodes_list[0]["id"]
        target_id = nodes_list[1]["id"]
        if source_id == target_id and len(nodes_list) > 2:
            target_id = nodes_list[2]["id"]
        
        if source_id != target_id:
            path, length, err = manager.find_shortest_path(source_id, target_id)
            if path:
                print(f"    Shortest Path PASSED for {source_id}-{target_id}.")
            else:
                print(f"    Shortest Path FAILED or no path for {source_id}-{target_id}: {err}")
                # Not a hard fail if no path is a valid outcome for test data
        else:
            print("    Shortest Path SKIPPED: Could not find distinct source/target.")

    print("  Testing Emergency Route via Manager...")
    if len(nodes_list) >= 2:
        source_id_em = nodes_list[0]["id"]
        # Try to find a facility for target
        facility_nodes_em = [n["id"] for n in nodes_list if n.get("type") == "Medical"]
        target_id_em = facility_nodes_em[0] if facility_nodes_em else nodes_list[-1]["id"]
        if source_id_em == target_id_em and len(nodes_list) > 1:
            source_id_em = nodes_list[1]["id"] if nodes_list[1]["id"] != target_id_em else (nodes_list[0]["id"] if nodes_list[0]["id"] != target_id_em else None)
        
        if source_id_em and target_id_em and source_id_em != target_id_em:
            em_path, em_length, em_err = manager.find_emergency_route(source_id_em, target_id_em)
            if em_path:
                print(f"    Emergency Route PASSED for {source_id_em}-{target_id_em}.")
            else:
                print(f"    Emergency Route FAILED or no path for {source_id_em}-{target_id_em}: {em_err}")
        else:
            print("    Emergency Route SKIPPED: Could not find distinct source/target for emergency test.")
    else:
        print("    Emergency Route SKIPPED: Not enough nodes.")

    print("  Testing Transit Demand Coverage via Manager...")
    coverage, err_cov = manager.get_transit_demand_coverage()
    if coverage and "error" not in coverage:
        print(f"    Transit Demand Coverage PASSED. Overall direct coverage: {coverage.get("percentage_any_direct_coverage", "N/A")}%")
    else:
        print(f"    Transit Demand Coverage FAILED: {err_cov or coverage.get("error")}")
        all_passed = False
        
    return all_passed

if __name__ == "__main__":
    init_ok = test_system_manager_initialization()
    if init_ok:
        test_system_manager_sample_operations()
    print("Integration (SystemManager) tests completed.")

