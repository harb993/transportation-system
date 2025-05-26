# Emergency Response Module

This module focuses on optimizing routes and simulating responses for emergency services (e.g., ambulances).

## Components

1.  **`astar_emergency.py`**:
    *   Implements the A* search algorithm to find the optimal path for emergency vehicles.
    *   Uses a heuristic (Euclidean distance based on coordinates) to guide the search.
    *   Considers time-dependent travel costs by adjusting edge weights based on traffic flow data for different times of day (similar to `dijkstra_time_dependent.py` but potentially with different congestion factors for emergency vehicles).
    *   Allows an `emergency_priority_factor` to be applied to edge weights, making emergency routes appear shorter/faster to the algorithm, thus prioritizing speed.
    *   Loads data from `road_data.json`, `facilities.json` (especially for hospital locations), and `traffic_data.json`.

2.  **`emergency_simulation.py`**:
    *   Provides a conceptual agent-based simulation for emergency response scenarios.
    *   Incidents are generated randomly or periodically at various locations.
    *   Emergency vehicles (agents) are dispatched from their current locations (or bases/hospitals) to incident sites.
    *   A* search (`astar_emergency_path`) is used to determine routes for vehicles to incidents and then from incidents to the nearest suitable medical facility.
    *   The simulation tracks vehicle status (available, enroute to incident, enroute to facility, at facility) and incident status (pending, assigned, resolved).
    *   Outputs a history of states at each simulation step, which can be used for visualization (e.g., generating PNG frames for an animation of vehicle movements and incident statuses).
    *   Includes a helper function to visualize individual simulation steps.

3.  **`response_analysis.py`**:
    *   Analyzes the output (history) from the `emergency_simulation.py`.
    *   Calculates key performance indicators (KPIs) for emergency response, such as:
        *   Average/median dispatch time (from incident report to vehicle assignment).
        *   Average/median travel time to incident (from assignment to arrival at scene).
        *   Average/median travel time to facility (from scene to hospital arrival).
        *   Average/median total resolution time (from incident report to hospital arrival).
    *   This analysis helps in evaluating the effectiveness of routing strategies and resource deployment.

## Data Dependencies

This module relies on the following JSON files from the `transportation_system/data/` directory:

*   `road_data.json`: For network topology, road attributes (distance, capacity), and node coordinates (used in A* heuristic).
*   `facilities.json`: Essential for identifying locations of medical facilities (hospitals), which are key destinations for emergency vehicles after patient pickup. Also used for general node information.
*   `traffic_data.json`: Provides time-dependent traffic flow data, allowing the A* routing to consider current congestion levels when finding optimal emergency routes.

## Usage

Each Python script can be run independently:

*   To find A* emergency paths: `python3.11 astar_emergency.py`
*   To run an emergency response simulation: `python3.11 emergency_simulation.py` (generates image frames in `output/visualizations/emergency_sim_frames/`)
*   To analyze simulation results: `python3.11 response_analysis.py` (requires a simulation history, e.g., a JSON file, as input; a dummy history is used for its standalone test).

These scripts will load data, perform calculations, and print outputs or save visualizations as detailed in their `if __name__ == "__main__":` blocks.

## Future Enhancements

*   More sophisticated dispatch logic (e.g., considering vehicle type, equipment, closest available and *appropriate* unit).
*   Dynamic rerouting of emergency vehicles based on real-time changes in traffic or incident priority.
*   Modeling of resource availability at hospitals.
*   Integration with predictive models for incident occurrence.

