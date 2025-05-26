import streamlit as st
import os
import sys
import pandas as pd # For displaying tables nicely
import re # For parsing potential line stations

# --- Add project root to sys.path to allow imports from other modules ---
TRANSPORTATION_SYSTEM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if TRANSPORTATION_SYSTEM_ROOT not in sys.path:
    sys.path.insert(0, TRANSPORTATION_SYSTEM_ROOT)

# Import SystemManager and other necessary components
from integration.system_manager import SystemManager

# --- Page Configuration ---
st.set_page_config(
    page_title="Cairo Smart Transport",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Caching SystemManager --- 
@st.cache_resource
def get_system_manager():
    manager = SystemManager()
    if not all([manager.infra_graph, manager.traffic_graph, manager.emergency_graph, manager.transit_data, manager.base_network_for_transit_viz]):
        st.error("Critical Error: SystemManager failed to load one or more essential data components. Please check data files and logs.")
        return None
    return manager

# --- Helper function to get node choices for selectboxes ---
@st.cache_data
def get_node_choices(_manager): 
    if _manager:
        nodes_info, err = _manager.get_all_node_ids_names()
        if err:
            st.warning(f"Could not fetch node list: {err}")
            return []
        return sorted(nodes_info, key=lambda x: x["name"])
    return []

# --- Page Implementations ---

def page_home():
    st.title("Welcome to the Greater Cairo Smart City Transportation System! 🚗💨")
    st.markdown("""
        This application provides tools for analyzing and optimizing various aspects of urban transportation
        in Greater Cairo. Use the sidebar to navigate through different modules:

        *   **Infrastructure Planning**: Design and analyze road network infrastructure.
        *   **Traffic Flow Optimization**: Find shortest paths, analyze congestion, and simulate traffic.
        *   **Emergency Response**: Optimize routes for emergency vehicles and analyze response times.
        *   **Public Transit Management**: Visualize and optimize metro and bus services.

        Select a module from the sidebar to begin.
    """)
    # Attempt to load image, provide alt text or placeholder if fails
    try:
        st.image(os.path.join(TRANSPORTATION_SYSTEM_ROOT, "docs", "smart_city_concept.jpg"), caption="Smart City Transportation Concept")
    except Exception:
        st.markdown("_(Conceptual image of Smart City Transportation)_ ")
        st.info("Note: A conceptual image for the homepage was intended here. If you have a relevant image, you can place it in `docs/smart_city_concept.jpg`.")


def page_infrastructure():
    st.header("🌉 Infrastructure Planning")
    manager = get_system_manager()
    if not manager: return

    node_options = get_node_choices(manager)
    node_name_to_id = {node["name"]: node["id"] for node in node_options}
    node_display_names = [node["name"] for node in node_options]

    st.subheader("Minimum Spanning Tree (MST) Network Design")
    with st.form(key="mst_form"):
        st.write("Configure MST parameters:")
        weight_key_options = {
            "Distance (km)": "distance_km", 
            "Cost (Million EGP - Potential Roads)": "cost_million_egp_potential",
            "Combined Score (Distance & Population)": "combined_score_dist_pop"
        }
        selected_weight_display = st.selectbox("Optimization Criterion (Weight Key)", list(weight_key_options.keys()), key="mst_weight_key")
        weight_key = weight_key_options[selected_weight_display]
        consider_potential = st.checkbox("Consider Potential New Roads for MST", value=True, key="mst_potential_roads")
        critical_facility_names = []
        if node_options:
            critical_facility_names = st.multiselect("Select Critical Facilities to Prioritize", options=node_display_names, key="mst_crit_facilities")
        critical_facility_ids = [node_name_to_id[name] for name in critical_facility_names]
        pop_threshold = st.slider("Population Threshold for Prioritization", 0, 1000000, 50000, 10000, key="mst_pop_thresh")
        pop_factor = st.slider("Population Weight Factor (for combined score)", 0.0, 1.0, 0.2, 0.05, key="mst_pop_factor")
        submit_button = st.form_submit_button(label="🔗 Generate MST Network")

    if submit_button:
        with st.spinner("Generating MST Network..."):
            mst_graph, analysis = manager.run_mst_analysis(weight_key, consider_potential, critical_facility_ids, pop_threshold, pop_factor)
            if mst_graph and analysis and "error" not in analysis:
                st.success("MST Network Generated Successfully!")
                st.subheader("MST Analysis Results")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Edges in MST", len(mst_graph.edges()))
                    if "total_network_distance_km" in analysis: st.metric("Total Distance (MST)", f"{analysis['total_network_distance_km']:.2f} km")
                    if "total_network_cost_million_egp" in analysis: st.metric("Total Cost (MST)", f"{analysis['total_network_cost_million_egp']:.2f} M EGP")
                with col2:
                    if "nodes_in_mst" in analysis: st.metric("Nodes in MST", analysis["nodes_in_mst"])
                    if "components" in analysis: st.metric("Network Components", analysis["components"])
                if "details" in analysis: st.write("Details:", analysis["details"])
                if "visualization_path" in analysis and analysis["visualization_path"] and os.path.exists(analysis["visualization_path"]):
                    st.image(analysis["visualization_path"], caption=f"MST Visualization ({selected_weight_display})")
                else: st.warning(f"MST visualization not available or path incorrect: {analysis.get("visualization_path")}")
            else: st.error(f"Failed to generate MST. Details: {analysis.get("error", analysis)}")
    st.markdown("---")
    st.subheader("Network Cost Analysis (Conceptual)")
    st.info("Further cost analysis tools can be added here.")

def page_traffic_flow():
    st.header("🚦 Traffic Flow Optimization")
    manager = get_system_manager()
    if not manager: return

    node_options = get_node_choices(manager)
    node_name_to_id = {node["name"]: node["id"] for node in node_options}
    node_display_names = [node["name"] for node in node_options]
    times_of_day = ["morning_peak", "mid_day", "afternoon_peak", "evening", "night"]

    st.subheader("Shortest Path Finder (Dijkstra)")
    with st.form(key="sp_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            sp_source_name = st.selectbox("Source Node", node_display_names, key="sp_source", index=0 if node_display_names else -1)
        with col2:
            sp_target_name = st.selectbox("Target Node", node_display_names, key="sp_target", index=min(1, len(node_display_names)-1) if node_display_names else -1)
        with col3:
            sp_tod = st.selectbox("Time of Day", times_of_day, key="sp_tod")
        sp_time_dependent = st.checkbox("Consider Time-Dependent Traffic", value=True, key="sp_time_dep")
        sp_weight = "time_seconds" if sp_time_dependent else "distance_km"
        submit_sp = st.form_submit_button("Find Shortest Path")
    
    if submit_sp and sp_source_name and sp_target_name:
        sp_source_id = node_name_to_id[sp_source_name]
        sp_target_id = node_name_to_id[sp_target_name]
        if sp_source_id == sp_target_id:
            st.warning("Source and Target nodes cannot be the same.")
        else:
            with st.spinner("Calculating shortest path..."):
                path, length, err = manager.find_shortest_path(sp_source_id, sp_target_id, sp_weight, sp_time_dependent, sp_tod)
                if err:
                    st.error(f"Error finding path: {err}")
                elif path:
                    st.success(f"Shortest path from {sp_source_name} to {sp_target_name}:")
                    st.write(f"**Path:** {' -> '.join(path)}")
                    st.write(f"**Effective {'Time' if sp_time_dependent else 'Distance'}:** {length:.2f} {'seconds' if sp_time_dependent else 'km'}")
                else: st.info("No path found between the selected nodes.")
    st.markdown("---")

    st.subheader("Congestion Analysis")
    with st.form(key="congestion_form"):
        cong_tod = st.selectbox("Select Time of Day for Congestion Analysis", times_of_day, key="cong_tod")
        cong_threshold = st.slider("Congestion Threshold (V/C Ratio)", 0.5, 1.5, 0.85, 0.05, key="cong_thresh")
        submit_cong = st.form_submit_button("Analyze Congestion")

    if submit_cong:
        with st.spinner("Analyzing congestion..."):
            levels, bottlenecks, viz_path, err = manager.analyze_congestion(cong_tod, cong_threshold)
            if err: st.error(f"Error in congestion analysis: {err}")
            elif levels is not None and bottlenecks is not None:
                st.success("Congestion Analysis Complete!")
                st.write(f"**Identified {len(bottlenecks)} bottlenecks (V/C > {cong_threshold}):**")
                if bottlenecks: st.dataframe(pd.DataFrame(bottlenecks, columns=["Road Segment (U-V)", "Congestion Level (V/C)"])) 
                else: st.info("No bottlenecks found above the specified threshold.")
                if viz_path and os.path.exists(viz_path): st.image(viz_path, caption=f"Congestion Map for {cong_tod}")
                else: st.warning(f"Congestion map not available or path incorrect: {viz_path}")
            else: st.error("Congestion analysis failed to return results.")
    st.markdown("---")
    st.subheader("Traffic Simulation Output")
    st.info("This section can display outputs from `traffic_simulation.py` (e.g., generated videos or key frames). Currently, it's a placeholder. You would typically run the simulation script separately and then view its output here or link to it.")
    sim_video_path = os.path.join(TRANSPORTATION_SYSTEM_ROOT, "output", "visualizations", "traffic_simulation.mp4")
    if os.path.exists(sim_video_path):
        st.video(sim_video_path)
    else:
        st.markdown(f"_Expected video at: `{sim_video_path}` (not found)_ ")

def page_emergency_response():
    st.header("🚑 Emergency Response Planning")
    manager = get_system_manager()
    if not manager: return

    node_options = get_node_choices(manager)
    node_name_to_id = {node["name"]: node["id"] for node in node_options}
    node_display_names = [node["name"] for node in node_options]
    times_of_day = ["morning_peak", "mid_day", "afternoon_peak", "evening", "night"]
    facility_options = [node for node in node_options if node.get("type") == "Medical"]
    facility_display_names = [node["name"] for node in facility_options]
    facility_name_to_id = {node["name"]: node["id"] for node in facility_options}

    st.subheader("A* Emergency Routing")
    with st.form(key="er_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            er_source_name = st.selectbox("Incident Location (Source)", node_display_names, key="er_source", index=0 if node_display_names else -1)
        with col2:
            er_target_name = st.selectbox("Destination Facility (e.g., Hospital)", facility_display_names if facility_display_names else node_display_names, key="er_target", index=0 if (facility_display_names or node_display_names) else -1)
        with col3:
            er_tod = st.selectbox("Time of Day", times_of_day, key="er_tod")
        er_priority = st.slider("Emergency Priority Factor (lower is faster)", 0.1, 1.0, 0.7, 0.05, key="er_priority")
        er_time_dependent = st.checkbox("Consider Time-Dependent Traffic", value=True, key="er_time_dep")
        er_weight = "time_seconds" if er_time_dependent else "distance_km"
        submit_er = st.form_submit_button("Find Emergency Route")

    if submit_er and er_source_name and er_target_name:
        er_source_id = node_name_to_id[er_source_name]
        er_target_id = facility_name_to_id.get(er_target_name, node_name_to_id.get(er_target_name)) # Handle if target was from general list
        if er_source_id == er_target_id: st.warning("Source and Target cannot be the same.")
        else:
            with st.spinner("Calculating emergency route..."):
                path, length, err = manager.find_emergency_route(er_source_id, er_target_id, er_weight, er_time_dependent, er_tod, er_priority)
                if err: st.error(f"Error finding emergency route: {err}")
                elif path: 
                    st.success(f"Emergency route from {er_source_name} to {er_target_name}:")
                    st.write(f"**Path:** {' -> '.join(path)}")
                    st.write(f"**Effective {'Time' if er_time_dependent else 'Distance'}:** {length:.2f} {'seconds' if er_time_dependent else 'km'}")
                else: st.info("No emergency route found.")
    st.markdown("---")
    st.subheader("Emergency Simulation & Response Analysis")
    st.info("This section can display outputs from `emergency_simulation.py` and `response_analysis.py`. Currently, it's a placeholder.")
    em_sim_video_path = os.path.join(TRANSPORTATION_SYSTEM_ROOT, "output", "visualizations", "emergency_simulation.mp4")
    if os.path.exists(em_sim_video_path):
        st.video(em_sim_video_path)
    else:
        st.markdown(f"_Expected video at: `{em_sim_video_path}` (not found)_ ")
    # Placeholder for response analysis stats
    # response_stats = manager.get_emergency_response_analysis() # Assuming such a method exists
    # if response_stats: st.json(response_stats)

def page_public_transit():
    st.header("🚌 Public Transit Management")
    manager = get_system_manager()
    if not manager: return

    node_options = get_node_choices(manager)
    node_name_to_id = {node["name"]: node["id"] for node in node_options}
    node_display_names = [node["name"] for node in node_options]

    st.subheader("Transit Network Visualization")
    if st.button("Show Full Transit Network Map", key="show_transit_map"):
        with st.spinner("Generating transit map..."):
            viz_path, err = manager.visualize_full_transit_network()
            if err: st.error(f"Error generating map: {err}")
            elif viz_path and os.path.exists(viz_path): st.image(viz_path, caption="Full Public Transit Network")
            else: st.warning(f"Transit map not available or path incorrect: {viz_path}")
    st.markdown("---")

    st.subheader("Bus Allocation Optimization")
    with st.form(key="bus_alloc_form"):
        current_buses_in_fleet = 0
        if manager.transit_data and "bus_routes" in manager.transit_data:
            current_buses_in_fleet = sum(r.get("Buses_Assigned",0) for r in manager.transit_data["bus_routes"])
        total_buses_input = st.number_input("Total Buses Available in Fleet", min_value=0, value=current_buses_in_fleet, step=5, key="total_buses")
        submit_bus_alloc = st.form_submit_button("Optimize Bus Allocation")
    
    if submit_bus_alloc:
        with st.spinner("Optimizing bus allocation..."):
            allocations, err = manager.run_bus_allocation_optimization(total_buses_input)
            if err: st.error(f"Error in bus allocation: {err}")
            elif allocations:
                st.success("Bus Allocation Optimized!")
                df_alloc = pd.DataFrame(list(allocations.items()), columns=["Route ID", "Allocated Buses"])
                st.dataframe(df_alloc)
                st.metric("Total Buses Allocated", sum(allocations.values()))
            else: st.error("Bus allocation failed.")
    st.markdown("---")

    st.subheader("Metro Line Feasibility Assessment")
    with st.form(key="metro_feas_form"):
        potential_line_input = st.text_input("Enter Potential Metro Line Stations (comma-separated Node IDs or Names)", placeholder="e.g., Maadi, Heliopolis, F3, 14", key="potential_line")
        submit_metro_feas = st.form_submit_button("Assess Feasibility")

    if submit_metro_feas and potential_line_input:
        # Parse input: try to map names to IDs, otherwise assume IDs
        raw_stations = [s.strip() for s in potential_line_input.split(",")]
        potential_line_stations_ids = []
        valid_input = True
        for station_name_or_id in raw_stations:
            station_id = node_name_to_id.get(station_name_or_id, station_name_or_id) # If not a name, assume it's an ID
            # Basic validation: check if ID exists (manager.infra_graph.has_node(station_id))
            if not manager.infra_graph.has_node(station_id):
                st.warning(f"Station '{station_name_or_id}' (resolved to '{station_id}') not found in network. Please check input.")
                valid_input = False
                break
            potential_line_stations_ids.append(station_id)
        
        if valid_input and potential_line_stations_ids:
            with st.spinner("Assessing metro line feasibility..."):
                assessment, err = manager.assess_metro_feasibility(potential_line_stations_ids)
                if err: st.error(f"Error in feasibility assessment: {err}")
                elif assessment:
                    st.success("Metro Line Feasibility Assessed!")
                    st.write(f"**Potential Line:** {' -> '.join(potential_line_stations_ids)}")
                    st.json(assessment) # Display full assessment dictionary
                else: st.error("Feasibility assessment failed.")
        elif valid_input and not potential_line_stations_ids:
             st.warning("Please enter valid station names or IDs.")

    st.markdown("---")
    st.subheader("Demand Coverage Analysis")
    if st.button("Analyze Public Transport Demand Coverage", key="analyze_demand"):
        with st.spinner("Analyzing demand coverage..."):
            coverage, err = manager.get_transit_demand_coverage()
            if err: st.error(f"Error in demand analysis: {err}")
            elif coverage:
                st.success("Demand Coverage Analysis Complete!")
                st.metric("Total Daily Demand (Passengers)", coverage["total_daily_demand_passengers"])
                st.metric("Directly Covered by Any Service (%)", f"{coverage['percentage_any_direct_coverage']:.2f}%")
                st.write("**Coverage Details:**")
                st.json({
                    "Metro Direct Coverage (%)": coverage["percentage_metro_direct_coverage"],
                    "Bus Direct Coverage (%)": coverage["percentage_bus_direct_coverage"],
                    "Passengers Directly Covered (Metro)": coverage["passengers_directly_covered_by_metro"],
                    "Passengers Directly Covered (Bus)": coverage["passengers_directly_covered_by_bus"],
                    "Uncovered O-D Pairs": coverage["number_of_uncovered_od_pairs"],
                    "Passengers in Uncovered O-D Pairs": coverage["total_passengers_in_uncovered_od_pairs"]
                })
                st.write("**Top 10 Uncovered Demand Pairs:**")
                if coverage.get("top_10_uncovered_demand_pairs"): 
                    st.dataframe(pd.DataFrame(coverage["top_10_uncovered_demand_pairs"])) 
                else: st.info("No uncovered demand pairs found or data not available.")
            else: st.error("Demand coverage analysis failed.")

# --- Main Application Logic (Sidebar Navigation) ---
def main():
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.radio(
        "Choose a Module:",
        ["Home", "Infrastructure Planning", "Traffic Flow Optimization", "Emergency Response", "Public Transit Management"]
    )
    

    if app_mode == "Home":
        page_home()
    elif app_mode == "Infrastructure Planning":
        page_infrastructure()
    elif app_mode == "Traffic Flow Optimization":
        page_traffic_flow()
    elif app_mode == "Emergency Response":
        page_emergency_response()
    elif app_mode == "Public Transit Management":
        page_public_transit()

if __name__ == "__main__":
    main()

