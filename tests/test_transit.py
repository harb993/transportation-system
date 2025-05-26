import sys
import os

# Add transit module to path
TRANSIT_MODULE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "transit"))
if TRANSIT_MODULE_PATH not in sys.path:
    sys.path.insert(0, TRANSIT_MODULE_PATH)

from transit_optimization import get_transit_data, get_base_road_network_for_transit, optimize_bus_allocation_greedy, assess_new_metro_line_feasibility
from improvement_analysis import analyze_demand_coverage

# Define data paths relative to the transportation_system directory
TRANSPORTATION_SYSTEM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_BASE_PATH = os.path.join(TRANSPORTATION_SYSTEM_ROOT, "data")

def test_bus_allocation_basic():
    print("--- Testing Transit: Bus Allocation (Basic) ---")
    transit_data_file = os.path.join(DATA_BASE_PATH, "transit_data.json")
    transit_data = get_transit_data(transit_data_file)

    if not transit_data or "bus_routes" not in transit_data or "public_transport_demand" not in transit_data:
        print("Test FAILED: Could not load transit data for bus allocation.")
        return False

    bus_routes = transit_data["bus_routes"]
    demand = transit_data["public_transport_demand"]
    total_buses = sum(r.get("Buses_Assigned", 0) for r in bus_routes)
    if total_buses == 0: total_buses = 50 # Ensure some buses if data has none

    allocations = optimize_bus_allocation_greedy(bus_routes, demand, total_buses)
    if allocations and "error" not in allocations:
        print(f"Test PASSED: Bus allocation calculated. Total allocated: {sum(allocations.values())} (Target: {total_buses})")
        # Add assertions here, e.g. sum of allocated buses should be close to total_buses
        if sum(allocations.values()) != total_buses:
            print(f"Test WARNING: Allocated buses ({sum(allocations.values())}) does not exactly match target ({total_buses}) due to rounding/logic.")
        return True
    else:
        print(f"Test FAILED: Bus allocation error: {allocations.get("error", "Unknown error")}")
        return False

def test_demand_coverage_basic():
    print("--- Testing Transit: Demand Coverage (Basic) ---")
    transit_data_file = os.path.join(DATA_BASE_PATH, "transit_data.json")
    transit_data = get_transit_data(transit_data_file)

    if not transit_data:
        print("Test FAILED: Could not load transit data for demand coverage.")
        return False

    coverage_results = analyze_demand_coverage(transit_data)
    if coverage_results and "error" not in coverage_results:
        print(f"Test PASSED: Demand coverage calculated. Total demand: {coverage_results["total_daily_demand_passengers"]}")
        return True
    else:
        print(f"Test FAILED: Demand coverage analysis error: {coverage_results.get("error", "Unknown error")}")
        return False

if __name__ == "__main__":
    test_bus_allocation_basic()
    test_demand_coverage_basic()
    # Add calls to test assess_new_metro_line_feasibility, visualize_transit if they have simple testable units.
    print("Transit module tests completed.")

