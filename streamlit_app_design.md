# Streamlit Application Design for Smart City Transportation System

## 1. Overall Structure

*   **Multi-page Application**: The application will use a sidebar for navigation between different modules/functionalities.
*   **Main Entry Point**: `integration/main.py` will be the Streamlit application script.
*   **System Backend**: The `integration/system_manager.py` will be used to interact with the backend logic of all modules.

## 2. Navigation (Sidebar)

The sidebar will list the main modules as selectable pages:

*   **Home/Overview**: A brief introduction to the system and its capabilities.
*   **Infrastructure Planning**:
    *   MST Network Design
    *   Network Cost Analysis
*   **Traffic Flow Optimization**:
    *   Shortest Path Finder (Dijkstra)
    *   K-Alternate Routes (Yen)
    *   Congestion Analysis & Visualization
    *   Traffic Simulation (View Output)
*   **Emergency Response**:
    *   A* Emergency Routing
    *   Emergency Simulation (View Output)
    *   Response Time Analysis (View Output)
*   **Public Transit Management**:
    *   Transit Network Visualization
    *   Bus Allocation Optimization
    *   Metro Line Feasibility Assessment
    *   Demand Coverage Analysis
*   **System Data Viewer**: (Optional) A page to view summaries of the loaded data (nodes, facilities).

## 3. Page Layouts (General Principles)

*   **Title**: Each page will have a clear title.
*   **Input Section**: User inputs (dropdowns for nodes, sliders for parameters, text inputs) will be grouped, often in an expander or a dedicated section.
*   **Action Button**: A button (e.g., "Run Analysis", "Find Path") to trigger the backend processing.
*   **Output Section**: Results will be displayed below the inputs, including:
    *   Text summaries (e.g., path details, costs, analysis results).
    *   Tables (e.g., for lists of routes, demand pairs).
    *   Visualizations (Matplotlib plots generated by backend, embedded using `st.pyplot()`). For simulations, it might link to generated videos or show key frames.

## 4. Key UI Components per Module

### 4.1. Home/Overview Page
*   Static content: Project description, how to use the app.

### 4.2. Infrastructure Planning
*   **MST Network Design**:
    *   Inputs: Weight key (distance, cost), consider potential roads (checkbox), critical facilities (multiselect), population threshold (slider/number input), population factor (slider/number input).
    *   Outputs: MST visualization, total cost/distance of MST.
*   **Network Cost Analysis** (Could be part of MST or separate):
    *   Inputs: Select potential roads to analyze.
    *   Outputs: Table of costs for selected roads.

### 4.3. Traffic Flow Optimization
*   **Shortest Path Finder**:
    *   Inputs: Source node (dropdown), Target node (dropdown), Time of day (select), Weight key (distance, time).
    *   Outputs: Path sequence, path length/time, visualization of path on map (if feasible to generate quickly).
*   **K-Alternate Routes**:
    *   Inputs: Source node, Target node, K value (number input), Weight key.
    *   Outputs: List of K paths with their lengths.
*   **Congestion Analysis**:
    *   Inputs: Time of day (select), Congestion threshold (slider).
    *   Outputs: Congestion map visualization, list of bottlenecks.
*   **Traffic Simulation**: 
    *   Display pre-generated simulation videos or key frames.
    *   (Advanced) Inputs to trigger a new (simplified/short) simulation run if computationally feasible for Streamlit.

### 4.4. Emergency Response
*   **A* Emergency Routing**:
    *   Inputs: Source node, Target node (often a hospital), Time of day, Priority factor (slider).
    *   Outputs: Optimized emergency route, effective length/time.
*   **Emergency Simulation**: Display pre-generated simulation videos/frames.
*   **Response Time Analysis**: Display summary statistics from simulation outputs (e.g., average response times).

### 4.5. Public Transit Management
*   **Transit Network Visualization**:
    *   Outputs: Map showing metro lines and bus routes.
    *   (Optional) Filters to show/hide specific lines/routes.
*   **Bus Allocation Optimization**:
    *   Inputs: Total buses available (number input).
    *   Outputs: Table of optimized bus allocations per route.
*   **Metro Line Feasibility**:
    *   Inputs: User defines a potential new metro line (e.g., by selecting a sequence of existing nodes/stations).
    *   Outputs: Feasibility score and rationale.
*   **Demand Coverage Analysis**:
    *   Outputs: Statistics on demand coverage, list of top uncovered O-D pairs.

### 4.6. System Data Viewer (Optional)
*   Display tables of loaded nodes, facilities, road segments (paginated if large).

## 5. Data Handling
*   The `SystemManager` will be instantiated once and cached (`@st.cache_resource` or `@st.singleton`) to load data and graphs efficiently.
*   Node selections will use lists of (ID, Name) fetched from `SystemManager`.

## 6. Visualizations
*   Matplotlib plots generated by backend functions will be displayed using `st.pyplot(fig)`.
*   For complex or animated visualizations (simulations), the app might link to pre-generated files in the `output/visualizations` directory or attempt to display them if Streamlit supports the format directly (e.g., `st.video`).

## 7. Error Handling and User Feedback
*   Use `st.spinner` for long-running operations.
*   Display error messages using `st.error()` if backend operations fail or inputs are invalid.
*   Provide informative messages using `st.info()` or `st.success()`.

This design document will guide the implementation of `integration/main.py`.
