# Infrastructure Module

This module focuses on the design and analysis of the city's transportation infrastructure, primarily road networks.

## Components

1.  **`kruskal_modified.py`**:
    *   Implements a modified version of Kruskal's algorithm to find the Minimum Spanning Tree (MST) of the road network.
    *   Considers options for including potential new roads.
    *   Allows prioritization of connections to critical facilities (e.g., hospitals) and high-population areas by adjusting edge weights.
    *   Can use different weight keys for MST calculation (e.g., `distance_km` for existing roads, `cost_million_egp` for potential new roads).
    *   Loads data from `road_data.json` and `facilities.json`.

2.  **`visualize_network.py`**:
    *   Provides functions to visualize the transportation network graph using Matplotlib and NetworkX.
    *   Can display the full network or highlight specific paths/edges (e.g., an MST).
    *   Uses geographic coordinates for node positioning if available, otherwise uses a spring layout.
    *   Color-codes nodes by type (Residential, Business, Medical, etc.) and includes a legend.
    *   Saves visualizations to image files (e.g., PNG).

3.  **`cost_analysis.py`**:
    *   Contains functions to analyze the costs associated with transportation infrastructure.
    *   Summarizes the total and average construction costs and distances of potential new road projects.
    *   Analyzes the total construction cost (for potential roads) and total network distance for a given MST or any selected set of roads.
    *   Loads data from `road_data.json`.

## Data Dependencies

This module primarily relies on the following JSON files located in the `transportation_system/data/` directory:

*   `road_data.json`: Contains information about neighborhoods (nodes) and both existing and potential roads (edges), including attributes like distance, capacity, condition, and construction costs for potential roads.
*   `facilities.json`: Contains information about important city facilities (nodes), including their type, ID, and coordinates. This is used for prioritization in MST calculations and for node information during visualization.

## Usage

Each Python script within this module can be run independently for testing or specific analysis tasks. They include `if __name__ == "__main__":` blocks with example usage.

*   To generate an MST: Run `python3.11 kruskal_modified.py`
*   To visualize the network: Run `python3.11 visualize_network.py` (this will save sample images to `output/visualizations/`)
*   To perform cost analysis: Run `python3.11 cost_analysis.py`

These scripts will typically load the necessary JSON data, perform their respective operations, and print results to the console or save output files (like images).

## Future Enhancements

*   Integration with a more robust graph database for larger datasets.
*   More sophisticated cost models, including maintenance and operational costs.
*   Inclusion of Prim's algorithm as an alternative for MST generation.
*   Interactive visualizations using libraries like Plotly or Bokeh.

