# Traffic Flow Module

This module is dedicated to analyzing and optimizing traffic flow within the city network. It includes algorithms for finding optimal routes, simulating traffic, and identifying congestion points.

## Components

1.  **`dijkstra_time_dependent.py`**:
    *   Implements Dijkstra's algorithm to find the shortest path between two locations.
    *   Crucially, it incorporates time-dependent travel costs by adjusting edge weights (e.g., distance or travel time) based on traffic flow data for different times of day (morning peak, afternoon, evening peak, night).
    *   A simple congestion model is used: `effective_weight = base_weight * (1 + traffic_flow / capacity)`.
    *   Loads data from `road_data.json`, `facilities.json`, and `traffic_data.json`.

2.  **`yen_alternate_routes.py`**:
    *   Implements Yen's K-shortest paths algorithm to find multiple (K) distinct shortest paths between a source and a target.
    *   This is useful for providing alternative routes or for more complex traffic distribution strategies.
    *   Uses a specified weight key (e.g., `distance_km`) for path calculation.
    *   Loads data from `road_data.json`, `facilities.json`, and `traffic_data.json` to build the graph.

3.  **`traffic_simulation.py`**:
    *   Provides a conceptual agent-based traffic simulation framework.
    *   Vehicles (agents) are initialized with random start and destination nodes.
    *   Agents attempt to move along their paths (calculated using simple Dijkstra) in discrete time steps.
    *   A simplified model for edge capacity and vehicle movement is used: vehicles move if the edge is not "full" based on a fraction of its hourly capacity.
    *   The simulation cycles through different times of day to vary traffic conditions (conceptually).
    *   Outputs a history of edge loads at each step, which can be used to generate visualizations (e.g., a series of PNG frames for an animation).
    *   Includes a helper function to visualize individual simulation steps, showing edge load via color and width.

4.  **`congestion_analysis.py`**:
    *   Calculates congestion levels for each road segment based on Volume/Capacity (V/C) ratios for a specified time of day.
    *   Identifies potential bottlenecks in the network where V/C ratio exceeds a defined threshold.
    *   Provides a function to visualize the congestion map, color-coding roads based on their V/C ratio (e.g., green for low, yellow for moderate, red for high congestion).
    *   Loads data from `road_data.json`, `facilities.json`, and `traffic_data.json`.

## Data Dependencies

This module relies on the following JSON files from the `transportation_system/data/` directory:

*   `road_data.json`: For network topology (nodes and edges), base road attributes like distance and capacity.
*   `facilities.json`: For node information, especially if facilities are origins or destinations.
*   `traffic_data.json`: Crucial for time-dependent analysis, providing vehicle flow rates (e.g., `Morning_Peak_veh_h`) for different road segments and times of day.

## Usage

Each Python script can be run independently for testing or specific analyses:

*   To find time-dependent shortest paths: `python3.11 dijkstra_time_dependent.py`
*   To find K-alternate routes: `python3.11 yen_alternate_routes.py`
*   To run a conceptual traffic simulation: `python3.11 traffic_simulation.py` (generates image frames in `output/visualizations/simulation_frames/`)
*   To analyze and visualize network congestion: `python3.11 congestion_analysis.py` (generates congestion maps in `output/visualizations/`)

These scripts will load data, perform calculations, and print outputs or save visualizations as specified in their `if __name__ == "__main__":` blocks.

## Future Enhancements

*   More sophisticated traffic simulation models (e.g., microscopic simulation, dynamic traffic assignment).
*   Integration of A* search for pathfinding, potentially with more advanced heuristics.
*   Real-time data ingestion capabilities for dynamic congestion updates.
*   Advanced congestion metrics and prediction models.

