import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
import sys
import os

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from system_manager import SystemManager
from traffic_flow.congestion_analysis import calculate_congestion_levels, identify_bottlenecks, visualize_congestion_map

# Initialize session state
if 'system_manager' not in st.session_state:
    st.session_state['system_manager'] = SystemManager()

# Page configuration
st.set_page_config(
    page_title="Transportation System Dashboard",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a module",
    ["Overview", "Infrastructure", "Traffic Flow", "Emergency Response", "Public Transit"]
)

def overview_page():
    st.title("Transportation System Overview")
    st.write("Welcome to the Transportation System Dashboard!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("System Statistics")
        if st.session_state.system_manager.infra_graph:
            graph = st.session_state.system_manager.infra_graph
            st.metric("Total Nodes", len(graph.nodes()))
            st.metric("Total Roads", len(graph.edges()))
    
    with col2:
        st.subheader("Quick Actions")
        if st.button("Refresh Data"):
            st.session_state.system_manager._load_all_graphs_and_data()
            st.success("Data refreshed successfully!")

def infrastructure_page():
    st.title("Infrastructure Analysis")
    
    # MST Analysis Section
    st.subheader("Minimum Spanning Tree Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        weight_key = st.selectbox(
            "Weight Metric",
            ["distance_km", "cost_million_egp"]
        )
        consider_potential = st.checkbox("Consider Potential Roads")
    
    with col2:
        pop_threshold = st.number_input("Population Threshold", value=0)
        pop_factor = st.number_input("Population Factor", value=0.1, min_value=0.0, max_value=1.0)
    
    if st.button("Run MST Analysis"):
        mst, analysis = st.session_state.system_manager.run_mst_analysis(
            weight_key=weight_key,
            consider_potential=consider_potential,
            pop_threshold=pop_threshold,
            pop_factor=pop_factor
        )
        
        if mst and isinstance(analysis, dict):
            st.success("MST Analysis completed successfully!")
            st.image(analysis["visualization_path"])
            
            # Display analysis results
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total MST Cost", f"{analysis.get('total_cost', 0):.2f}")
            with col2:
                st.metric("Number of Edges", len(mst.edges()))

def get_available_nodes():
    system_manager = st.session_state.system_manager
    if system_manager.traffic_graph:
        return sorted(list(system_manager.traffic_graph.nodes()))
    return []

def traffic_flow_page():
    st.title("Traffic Flow Analysis")
    
    # Get available nodes
    nodes = get_available_nodes()
    if not nodes:
        st.error("No nodes available. Please check if the traffic graph is loaded correctly.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Path Finding")
        source = st.selectbox("Source Node", nodes, key="traffic_source")
        target = st.selectbox("Target Node", nodes, key="traffic_target")
        time_dependent = st.checkbox("Consider Time-Dependent Traffic")
        
        if time_dependent:
            tod = st.slider("Time of Day (hour)", 0, 23, 12)
        else:
            tod = None
            
        if st.button("Find Path"):
            path, length, message = st.session_state.system_manager.find_shortest_path(
                source, target, time_dependent=time_dependent, tod=tod
            )
            if path:
                st.success(f"Path found! Length: {length:.2f}")
                st.write("Path:", " → ".join(path))
            else:
                st.error(message)
    
    with col2:
        st.subheader("Congestion Analysis")
        if st.button("Analyze Congestion"):
            graph = st.session_state.system_manager.traffic_graph
            congestion_levels = calculate_congestion_levels(graph)
            bottlenecks = identify_bottlenecks(graph, congestion_levels)
            
            # Display congestion map
            fig = visualize_congestion_map(graph, congestion_levels)
            st.plotly_chart(fig)
            
            # Display bottlenecks
            st.write("Critical Bottlenecks:", bottlenecks)

def emergency_response_page():
    st.title("Emergency Response System")
    
    # Get available nodes
    nodes = get_available_nodes()
    if not nodes:
        st.error("No nodes available. Please check if the emergency graph is loaded correctly.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Emergency Route Planning")
        emergency_type = st.selectbox(
            "Emergency Type",
            ["Fire", "Medical", "Police"]
        )
        
        source = st.selectbox("Emergency Source Location", nodes, key="emergency_source")
        target = st.selectbox("Emergency Target Location", nodes, key="emergency_target")
        
        if st.button("Calculate Emergency Route"):
            path, cost = st.session_state.system_manager.a_star_emergency_path(
                source, target, emergency_type
            )
            if path:
                st.success(f"Emergency route found! ETA: {cost:.2f} minutes")
                st.write("Route:", " → ".join(path))
            else:
                st.error("Could not find a valid route")

def transit_page():
    st.title("Public Transit Network")
    
    tab1, tab2 = st.tabs(["Network Analysis", "Optimization"])
    
    with tab1:
        st.subheader("Transit Network Visualization")
        if st.button("Show Transit Network"):
            st.session_state.system_manager.visualize_transit_network()
            st.image("transit_network.png")
    
    with tab2:
        st.subheader("Route Optimization")
        if st.button("Optimize Bus Allocation"):
            result = st.session_state.system_manager.optimize_bus_allocation_greedy()
            if result:
                st.success("Bus allocation optimized!")
                st.write(result)

# Route to appropriate page
if page == "Overview":
    overview_page()
elif page == "Infrastructure":
    infrastructure_page()
elif page == "Traffic Flow":
    traffic_flow_page()
elif page == "Emergency Response":
    emergency_response_page()
elif page == "Public Transit":
    transit_page()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Made with ❤️ using Streamlit")
