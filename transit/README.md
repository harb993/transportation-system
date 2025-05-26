# Public Transit Module

This module handles the optimization, visualization, and analysis of the city_s public transit network, including metro lines and bus routes.

## Components

1.  **`transit_optimization.py`**:
    *   Includes conceptual algorithms for public transit optimization.
    *   `optimize_bus_allocation_greedy`: A simplified greedy approach to allocate a total number of available buses across different routes. The allocation is proportional to a calculated "priority score" for each route (e.g., based on passenger demand).
    *   `assess_new_metro_line_feasibility`: A conceptual function to assess the potential of a new metro line. It calculates a score based on how much currently uncovered O-D demand the new line would serve and its connectivity to existing transit hubs or important facilities.
    *   Loads data from `transit_data.json` (for existing routes, demand) and `road_data.json`/`facilities.json` (for network context).

2.  **`visualize_transit.py`**:
    *   Provides functions to visualize the public transit network (metro and bus lines) overlaid on the base city map (nodes representing neighborhoods/facilities).
    *   Uses Matplotlib and NetworkX for plotting.
    *   Metro lines and bus routes are drawn with distinct colors and styles.
    *   Node positions are based on coordinates if available, otherwise a spring layout is used.
    *   Includes a legend for different transit lines and node types.
    *   Saves visualizations to image files.

3.  **`improvement_analysis.py`**:
    *   Analyzes the effectiveness of the current (or optimized) public transit system in meeting passenger demand.
    *   `analyze_demand_coverage`: Calculates the percentage of total O-D passenger demand that is directly covered by existing metro lines and/or bus routes. It identifies O-D pairs with no direct service and lists top uncovered demand pairs.
    *   `suggest_route_extensions_or_new_routes`: Provides conceptual suggestions for new transit routes or extensions of existing ones based on the identified high-demand uncovered O-D pairs. These are high-level suggestions that would require further detailed study.

## Data Dependencies

This module primarily relies on the following JSON files from the `transportation_system/data/` directory:

*   `transit_data.json`: This is the core data file, containing:
    *   `metro_lines`: Information about existing metro lines, including their stations and daily passenger counts.
    *   `bus_routes`: Details of bus routes, including their stops, number of buses currently assigned, and daily passenger counts.
    *   `public_transport_demand`: A list of Origin-Destination (O-D) pairs with the number of daily passengers demanding travel between them.
*   `road_data.json` and `facilities.json`: Used to build the base map of nodes (neighborhoods, facilities) and their locations, providing context for transit routes and demand points.

## Usage

Each Python script can be run independently for specific tasks:

*   To run conceptual transit optimization functions: `python3.11 transit_optimization.py`
*   To visualize the transit network: `python3.11 visualize_transit.py` (saves images to `output/visualizations/`)
*   To analyze demand coverage and get improvement suggestions: `python3.11 improvement_analysis.py`

These scripts will load the necessary data, perform their analyses or visualizations, and print results or save output files as indicated in their `if __name__ == "__main__":` blocks.

## Future Enhancements

*   More sophisticated transit assignment models (e.g., considering transfers, travel time, frequency).
*   Dynamic programming or other OR techniques for route design and scheduling.
*   Cost-benefit analysis for new transit projects.
*   Integration with real-time passenger count data or smart card data.
*   Multi-modal routing considering walking, cycling, and transit.

