import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import os
import tempfile
from congestion_analysis import get_full_traffic_graph, calculate_congestion_levels, identify_bottlenecks, visualize_congestion_map
from dijkstra_time_dependent import dijkstra_time_dependent
from yen_alternate_routes import yen_k_shortest_paths
from traffic_simulation import TrafficSimulator, visualize_simulation_step

def load_traffic_graph():
    base_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    road_file = os.path.join(base_path, "road_data.json")
    facilities_file = os.path.join(base_path, "facilities.json")
    traffic_file = os.path.join(base_path, "traffic_data.json")
    
    return get_full_traffic_graph(road_file, facilities_file, traffic_file)

def main():
    st.set_page_config(page_title="Traffic Flow Analysis", layout="wide")
    
    st.title("Traffic Flow Analysis Dashboard")
    st.write("Analyze traffic patterns, congestion, and routing options in the transportation network")

    # Load data
    traffic_graph = load_traffic_graph()
    
    if not traffic_graph:
        st.error("Failed to load traffic data")
        return

    # Create tabs for different analyses
    tab1, tab2, tab3 = st.tabs(["Congestion Analysis", "Route Planning", "Traffic Simulation"])

    with tab1:
        st.header("Congestion Analysis")
        
        # Time period selection
        time_period = st.selectbox(
            "Select Time Period",
            ["morning_peak", "afternoon", "evening_peak", "night"]
        )
        
        # Calculate congestion
        congestion_data = calculate_congestion_levels(traffic_graph, time_period)
        
        if congestion_data:
            # Find bottlenecks
            threshold = st.slider("Congestion Threshold (V/C Ratio)", 0.5, 1.5, 0.85)
            bottlenecks = identify_bottlenecks(congestion_data, threshold)
            
            # Display bottlenecks
            st.subheader(f"Critical Bottlenecks (V/C ≥ {threshold})")
            if bottlenecks:
                for i, bn in enumerate(bottlenecks[:5]):
                    st.metric(
                        f"Bottleneck {i+1}: {bn['from_node']} → {bn['to_node']}", 
                        f"V/C Ratio: {bn['vc_ratio']:.2f}",
                        f"Volume: {bn['volume']} veh/h"
                    )
            else:
                st.info("No bottlenecks found at current threshold.")
            
            # Visualize congestion map
            st.subheader("Congestion Map")
            fig_path = os.path.join(tempfile.mkdtemp(), "congestion_map.png")
            visualize_congestion_map(traffic_graph, congestion_data, time_period, 
                                   output_path=fig_path, threshold=threshold)
            if os.path.exists(fig_path):
                st.image(fig_path)
                os.remove(fig_path)

    with tab2:
        st.header("Route Planning")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Source and destination selection
            nodes = sorted(list(traffic_graph.nodes()))
            source = st.selectbox("Select Source", nodes, index=0)
            destination = st.selectbox("Select Destination", nodes, index=min(1, len(nodes)-1))
        
        with col2:
            # Routing options
            time_of_day = st.selectbox(
                "Time of Day",
                ["morning_peak", "afternoon", "evening_peak", "night"]
            )
            consider_traffic = st.checkbox("Consider Traffic Conditions", value=True)
            num_alternatives = st.slider("Number of Alternative Routes", 1, 5, 3)
        
        if st.button("Find Routes"):
            if source != destination:
                # Get primary route using time-dependent Dijkstra
                path, length = dijkstra_time_dependent(
                    traffic_graph, source, destination,
                    time_dependent=consider_traffic,
                    time_of_day=time_of_day
                )
                
                if path:
                    st.subheader("Primary Route")
                    st.write(f"Path: {' → '.join(path)}")
                    st.write(f"Effective Length: {length:.2f} km")
                    
                    # Get alternative routes using Yen's algorithm
                    if num_alternatives > 1:
                        st.subheader("Alternative Routes")
                        alt_paths = yen_k_shortest_paths(
                            traffic_graph, source, destination,
                            K=num_alternatives
                        )
                        
                        for i, alt_path in enumerate(alt_paths[1:], 1):
                            alt_length = sum(traffic_graph[alt_path[j]][alt_path[j+1]]["distance_km"] 
                                          for j in range(len(alt_path)-1))
                            st.write(f"Alternative {i}: {' → '.join(alt_path)}")
                            st.write(f"Distance: {alt_length:.2f} km")
                else:
                    st.error("No route found between selected points.")
            else:
                st.warning("Source and destination must be different.")

    with tab3:
        st.header("Traffic Simulation")
        
        # Simulation parameters
        num_vehicles = st.slider("Number of Vehicles", 50, 500, 200)
        num_steps = st.slider("Simulation Steps", 10, 100, 50)
        
        if st.button("Run Simulation"):
            simulator = TrafficSimulator(traffic_graph, num_vehicles=num_vehicles, 
                                      simulation_steps=num_steps)
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Run simulation and show progress
            simulation_history = []
            time_of_day_cycle = ["morning_peak", "afternoon", "evening_peak", "night"] * (num_steps // 4 + 1)
            
            for i in range(num_steps):
                current_tod = time_of_day_cycle[i % len(time_of_day_cycle)]
                simulator.step(current_tod)
                simulation_history.append(simulator.history[-1])
                
                # Update progress
                progress = (i + 1) / num_steps
                progress_bar.progress(progress)
                status_text.text(f"Step {i+1}/{num_steps} ({current_tod})")
            
            st.success("Simulation completed!")
            
            # Show final state visualization
            st.subheader("Final Traffic State")
            fig_path = os.path.join(tempfile.mkdtemp(), "final_state.png")
            visualize_simulation_step(traffic_graph, simulation_history[-1], 
                                    num_steps, output_dir=os.path.dirname(fig_path))
            if os.path.exists(fig_path):
                st.image(fig_path)
                os.remove(fig_path)

if __name__ == "__main__":
    main()