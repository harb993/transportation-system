import streamlit as st
import pandas as pd
import folium
import os
import json
from pathlib import Path

# Set up paths
current_dir = Path(__file__).parent
output_dir = current_dir.parent / 'output'
graphs_dir = output_dir / 'graphs'
reports_dir = output_dir / 'reports'

# Set page configuration
st.set_page_config(
    page_title="Transit Network Visualization",
    page_icon="🚇",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stTitle {
        color: #2c3e50;
        font-size: 2.5rem !important;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .section-header {
        color: #34495e;
        font-size: 1.8rem !important;
        font-weight: bold;
        margin: 1.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("Transit Network Analysis Dashboard")

# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["Transit Network Map", "Transportation Network Map", "Network Statistics"])

def load_html_file(file_path):
    try:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        st.error(f"Error loading file {file_path.name}: {str(e)}")
        return None

with tab1:
    st.markdown("### Transit Network Visualization")
    transit_map_path = graphs_dir / 'transit_network_interactive.html'
    html_data = load_html_file(transit_map_path)
    if html_data:
        st.components.v1.html(html_data, height=600)

with tab2:
    st.markdown("### Transportation Network Visualization")
    transport_map_path = graphs_dir / 'transportation_network_interactive.html'
    html_data = load_html_file(transport_map_path)
    if html_data:
        st.components.v1.html(html_data, height=600)

with tab3:
    st.markdown("### Network Statistics Summary")
    stats_file = reports_dir / 'summary.txt'
    try:
        if not stats_file.exists():
            raise FileNotFoundError(f"Statistics file not found: {stats_file}")
            
        with open(stats_file, 'r') as f:
            stats = f.read()
        
        # Split the statistics into sections
        sections = stats.split('\n\n')
        
        for section in sections:
            if section.strip():
                # Extract section title and content
                lines = section.strip().split('\n')
                if lines:
                    # Make the section title into a header
                    st.subheader(lines[0])
                    # Create an expander for the content
                    with st.expander("Show Details", expanded=True):
                        # Display the rest of the content
                        for line in lines[1:]:
                            if line.strip():
                                st.text(line)
                st.markdown("---")
                
    except Exception as e:
        st.error(f"Error loading network statistics: {str(e)}")

# Add information about data freshness
st.sidebar.markdown("### Dashboard Information")
try:
    transit_map_time = os.path.getmtime(transit_map_path)
    st.sidebar.info(f"Last updated: {pd.to_datetime(transit_map_time, unit='s').strftime('%Y-%m-%d %H:%M:%S')}")
except Exception:
    st.sidebar.warning("Last update time unavailable")

# Footer
st.markdown("---")
st.markdown("*Transit Network Analysis Dashboard - Created with Streamlit*")