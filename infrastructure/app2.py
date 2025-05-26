import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import os
import json
import tempfile
from kruskal_modified import get_infrastructure_graph, kruskal_mst_modified
from cost_analysis import analyze_potential_road_costs, analyze_mst_cost
from visualize import visualize_network_on_map

def load_data():
    base_path = r"c:\Users\abdoo\Desktop\transportation_system\data"
    road_data_file = os.path.join(base_path, "road_data.json")
    facilities_data_file = os.path.join(base_path, "facilities.json")
    
    # Load graph
    infra_graph = get_infrastructure_graph(road_data_file, facilities_data_file)
    return infra_graph

def main():
    st.set_page_config(page_title="Infrastructure Analysis", layout="wide")
    
    st.title("Transportation Infrastructure Analysis")
    st.write("Analyze and visualize the transportation network infrastructure")

    # Load data
    infra_graph = load_data()
    
    if not infra_graph:
        st.error("Failed to load infrastructure data")
        return

    # Create tabs
    tab1, tab2 = st.tabs(["MST Analysis", "Cost Analysis"])

    with tab1:
        st.header("Minimum Spanning Tree Analysis")
        
        # Generate MST with default values
        mst = kruskal_mst_modified(
            infra_graph,
            weight_key="distance_km",
            consider_potential_roads=True,
            critical_facility_ids=["F3", "F4", "F5", "F6", "F9", "F10"]
        )

        # Create and display interactive map
        folium_map = visualize_network_on_map(infra_graph, mst)
        
        # Save the map to a temporary HTML file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
            folium_map.save(tmp.name)
            # Display the map using streamlit components
            st.components.v1.html(open(tmp.name, 'r').read(), height=600)
        
        # Clean up the temporary file
        os.unlink(tmp.name)

    with tab2:
        st.header("Cost Analysis")
        
        # Read the cost summary file
        cost_summary_path = r"C:\Users\abdoo\Desktop\transportation_system\output\reports\cost_summary.txt"
        with open(cost_summary_path, 'r') as f:
            cost_data = f.read()

        # Parse and display Potential Road Costs Summary
        st.subheader("Potential Road Costs Summary")
        summary_lines = [line for line in cost_data.split('\n') if line.strip()]
        
        # Extract metrics
        metrics = {}
        for line in summary_lines:
            if "Number of potential road projects:" in line:
                metrics["Number of Projects"] = int(line.split(":")[1].strip())
            elif "Total estimated cost:" in line:
                metrics["Total Cost"] = line.split(":")[1].strip()
            elif "Average cost per project:" in line:
                metrics["Average Cost/Project"] = line.split(":")[1].strip()
            elif "Total distance of potential roads:" in line:
                metrics["Total Distance"] = line.split(":")[1].strip()
            elif "Average distance per road:" in line:
                metrics["Average Distance/Road"] = line.split(":")[1].strip()

        # Display metrics in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Number of Projects", metrics["Number of Projects"])
            st.metric("Total Cost", metrics["Total Cost"])
        with col2:
            st.metric("Total Distance", metrics["Total Distance"])
            st.metric("Average Cost/Project", metrics["Average Cost/Project"])
        with col3:
            st.metric("Average Distance/Road", metrics["Average Distance/Road"])

        # Display Top 3 Most Expensive Roads
        st.subheader("Top 3 Most Expensive Potential Roads")
        start_idx = cost_data.find("Top 3 Most Expensive Potential Roads:")
        end_idx = cost_data.find("Minimum Spanning Tree Analysis")
        top_3_section = cost_data[start_idx:end_idx].split('\n')
        
        current_road = {}
        for line in top_3_section:
            if line.startswith(('1.', '2.', '3.')):
                if current_road:
                    with st.expander(f"From {current_road['from']} to {current_road['to']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Cost", current_road['cost'])
                            st.metric("Distance", current_road['distance'])
                        with col2:
                            st.metric("Capacity", current_road['capacity'])
                current_road = {'from': line.split('From')[1].split('to')[0].strip(),
                              'to': line.split('to')[1].strip()}
            elif 'Cost:' in line:
                current_road['cost'] = line.split('Cost:')[1].strip()
            elif 'Distance:' in line:
                current_road['distance'] = line.split('Distance:')[1].strip()
            elif 'Estimated Capacity:' in line:
                current_road['capacity'] = line.split('Estimated Capacity:')[1].strip()
        
        # Show last road
        if current_road:
            with st.expander(f"From {current_road['from']} to {current_road['to']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cost", current_road['cost'])
                    st.metric("Distance", current_road['distance'])
                with col2:
                    st.metric("Capacity", current_road['capacity'])

if __name__ == "__main__":
    main()