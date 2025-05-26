import json
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import os
import folium
from math import sqrt


"""the isolated nodes
F3 (Cairo University)
F4 (Al-Azhar University)
F5 (Egyptian Museum)
F6 (Cairo International Stadium)
F9 (Qasr El Aini Hospital)
F10 (Maadi Military Hospital)
Total isolated nodes: 6 """

def load_json_data(filename):
    """Load and return JSON data from a file"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points"""
    return sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

# Load data
facilities_path = os.path.join(os.path.dirname(__file__), 'facilities.json')
road_data_path = os.path.join(os.path.dirname(__file__), 'road_data.json')

facilities_data = load_json_data(facilities_path)
road_data = load_json_data(road_data_path)

# Create graph
G = nx.Graph()

# Add neighborhoods
for node in facilities_data['neighborhoods']:    # Use ID as is for neighborhoods
    node_id = str(node['ID'])
    G.add_node(
        node_id,  # Use ID as is
        name=node['Name'],
        type=node['Type'],
        x_coord=float(node['X_coordinate']),
        y_coord=float(node['Y_coordinate']),
        pos=(node['X_coordinate'], node['Y_coordinate']),  # Keep for compatibility
        node_category='neighborhood'
    )

# Add facility nodes
for facility in facilities_data['facilities']:    G.add_node(
        facility['ID'],
        name=facility['Name'],
        type=facility['Type'],
        x_coord=float(facility['X_coordinate']),
        y_coord=float(facility['Y_coordinate']),
        pos=(facility['X_coordinate'], facility['Y_coordinate']),  # Keep for compatibility
        node_category='facility'
    )

# Add road edges if they exist in road_data
if 'edges' in road_data:
    for edge in road_data['edges']:
        source = str(edge['FromID']).strip()  # Ensure string and remove whitespace
        target = str(edge['ToID']).strip()    # Ensure string and remove whitespace
          # No need to add prefixes, IDs are used as is
        # Just ensure they are strings
        source = str(source)
        target = str(target)
            
        # Debug print to check node existence
        if source not in G.nodes or target not in G.nodes:
            print(f"Warning: Edge {source}-{target} references non-existent node(s)")
            continue
          # Calculate distance based on coordinates
        source_coords = (G.nodes[source]['x_coord'], G.nodes[source]['y_coord'])
        target_coords = (G.nodes[target]['x_coord'], G.nodes[target]['y_coord'])
        distance = calculate_distance(source_coords, target_coords)
        
        # Determine road type based on capacity and status
        road_type = "major_road"  # default type
        if edge['status'] == 'potential':
            road_type = "potential_road"
        elif edge.get('Current_Capacity_vehicles_hour', 0) < 2500:
            road_type = "minor_road"
        elif edge.get('Current_Capacity_vehicles_hour', 0) >= 3500:
            road_type = "highway"
            
        G.add_edge(source, target, 
                  weight=distance,
                  type=road_type,
                  status=edge['status'],
                  capacity=edge.get('Current_Capacity_vehicles_hour', edge.get('Estimated_Capacity_vehicles_hour', 0)),
                  condition=edge.get('Condition_1_10', 0))

# Set up output directory
output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'graphs')
os.makedirs(output_dir, exist_ok=True)

# Create interactive map using folium
cairo_center = [30.05, 31.25]  # Approximate center of Cairo
m = folium.Map(location=cairo_center, zoom_start=11)

# Add nodes to the map
for node, data in G.nodes(data=True):
    # Folium uses lat/lon (y,x) while our data is in (x,y)
    location = [data['y_coord'], data['x_coord']]
    
    # Customize icon based on node category and type
    if data['node_category'] == 'neighborhood':
        color = 'blue'
        prefix = 'fa'
        icon = 'home'
    else:  # facility
        color = 'red'
        if data['type'] == 'Medical':
            icon = 'plus'
        elif data['type'] == 'Education':
            icon = 'graduation-cap'
        elif data['type'] == 'Airport':
            icon = 'plane'
        elif data['type'] == 'Business':
            icon = 'building'
        elif data['type'] == 'Commercial':
            icon = 'shopping-cart'
        else:
            icon = 'star'
    
    popup_text = f"""
    <b>{data['name']}</b><br>
    Type: {data['type']}<br>
    Category: {data['node_category']}
    """
    
    folium.Marker(
        location=location,
        popup=popup_text,
        icon=folium.Icon(color=color, icon=icon, prefix=prefix)
    ).add_to(m)

# Add edges to the map with different colors based on type
edge_colors = {
    'highway': 'red',
    'major_road': 'blue',
    'minor_road': 'gray',
    'potential_road': 'green',
    'facility_connection': 'orange'
}

for u, v, data in G.edges(data=True):
    # Convert to lat/lon format using x_coord and y_coord
    coordinates = [[G.nodes[u]['y_coord'], G.nodes[u]['x_coord']], 
                  [G.nodes[v]['y_coord'], G.nodes[v]['x_coord']]]
    
    road_type = data['type']
    color = edge_colors.get(road_type, 'gray')
    weight = 3 if road_type == 'highway' else 2
    dash_array = '10,10' if road_type == 'potential_road' else None
    
    popup_text = f"""
    Road Type: {road_type}<br>
    Status: {data.get('status', 'N/A')}<br>
    Capacity: {data.get('capacity', 'N/A')} vehicles/hour<br>
    Condition: {data.get('condition', 'N/A')}/10
    """
    
    folium.PolyLine(
        coordinates,
        weight=weight,
        color=color,
        popup=popup_text,
        dash_array=dash_array
    ).add_to(m)

# Save interactive map
map_path = os.path.join(output_dir, 'transportation_network_interactive.html')
m.save(map_path)

# Create static visualization with matplotlib
plt.figure(figsize=(15, 10))

# Get positions from x_coord and y_coord
positions = {node: (data['x_coord'], data['y_coord']) for node, data in G.nodes(data=True)}

# Print all nodes for debugging
print("\nAll nodes in graph:")
for node in G.nodes():
    print(f"Node {node}: {G.nodes[node]['name']} ({G.nodes[node]['type']})")

# Find isolated nodes
isolated_nodes = list(nx.isolates(G))
print("\nIsolated Nodes:")
for node in isolated_nodes:
    print(f"Node {node}: {G.nodes[node]['name']} ({G.nodes[node]['type']})")

# Draw neighborhoods
neighborhood_nodes = [n for n, d in G.nodes(data=True) if d.get('node_category') == 'neighborhood']
neighborhood_types = {d['type'] for _, d in G.nodes(data=True) if d.get('node_category') == 'neighborhood'}
neighborhood_colors = plt.cm.Set3(np.linspace(0, 1, len(neighborhood_types)))

# Draw non-isolated neighborhoods
for ntype, color in zip(neighborhood_types, neighborhood_colors):
    nodes = [n for n in neighborhood_nodes if G.nodes[n]['type'] == ntype and n not in isolated_nodes]
    nx.draw_networkx_nodes(G, positions, nodelist=nodes,
                         node_color=[color], node_size=300,
                         label=f'Neighborhood ({ntype})')

# Draw isolated neighborhoods with red border
isolated_neighborhoods = [n for n in neighborhood_nodes if n in isolated_nodes]
if isolated_neighborhoods:
    nx.draw_networkx_nodes(G, positions, nodelist=isolated_neighborhoods,
                          node_color='white', node_size=300,
                          edgecolors='red', linewidths=2,
                          label='Isolated Neighborhoods')

# Draw facility nodes by type
facility_nodes = [n for n, d in G.nodes(data=True) if d.get('node_category') == 'facility']
facility_types = {d['type'] for _, d in G.nodes(data=True) if d.get('node_category') == 'facility'}
facility_colors = plt.cm.Paired(np.linspace(0, 1, len(facility_types)))

# Draw non-isolated facilities
for ftype, color in zip(facility_types, facility_colors):
    nodes = [n for n in facility_nodes if G.nodes[n]['type'] == ftype and n not in isolated_nodes]
    nx.draw_networkx_nodes(G, positions, nodelist=nodes,
                         node_color=[color], node_size=200, node_shape='s',
                         label=f'Facility ({ftype})')

# Draw isolated facilities with red border
isolated_facilities = [n for n in facility_nodes if n in isolated_nodes]
if isolated_facilities:
    nx.draw_networkx_nodes(G, positions, nodelist=isolated_facilities,
                          node_color='white', node_size=200, node_shape='s',
                          edgecolors='red', linewidths=2,
                          label='Isolated Facilities')

# Draw edges by type
edge_colors = {
    'highway': 'red',
    'major_road': 'blue',
    'minor_road': 'gray',
    'potential_road': 'lightgreen',
    'facility_connection': 'lightblue'
}

edge_styles = {
    'highway': 'solid',
    'major_road': 'solid',
    'minor_road': 'solid',
    'potential_road': 'dashed',
    'facility_connection': 'dotted'
}

# Create an interactive map using folium
cairo_center = [30.05, 31.25]  # Approximate center of Cairo
m = folium.Map(location=cairo_center, zoom_start=11)

# Add nodes to the map
for node in G.nodes():
    data = G.nodes[node]
    pos = data['pos']
    # Folium uses lat/lon (y,x) while our data is in (x,y)
    location = [pos[1], pos[0]]
    
    # Customize icon based on node category and type
    if data['node_category'] == 'neighborhood':
        icon_color = 'blue'
        prefix = 'fa'
        icon = 'building'
    else:  # facility
        icon_color = 'red'
        if data['type'] == 'Medical':
            icon = 'plus'
        elif data['type'] == 'Education':
            icon = 'graduation-cap'
        elif data['type'] == 'Airport':
            icon = 'plane'
        elif data['type'] == 'Business':
            icon = 'briefcase'
        elif data['type'] == 'Commercial':
            icon = 'shopping-cart'
        else:
            icon = 'star'
        prefix = 'fa'
    
    # Create popup content
    popup_content = f"""
    <div style='min-width: 200px'>
        <h4>{data['name']}</h4>
        <b>Type:</b> {data['type']}<br>
        <b>Category:</b> {data['node_category']}<br>
        <b>ID:</b> {node}
    </div>
    """
    
    # Add marker
    folium.Marker(
        location=location,
        popup=folium.Popup(popup_content, max_width=300),
        icon=folium.Icon(color=icon_color, icon=icon, prefix=prefix),
        tooltip=data['name']
    ).add_to(m)

# Add edges (roads) to the map
for (u, v, data) in G.edges(data=True):
    # Get coordinates for the edge
    coordinates = [[G.nodes[u]['y_coord'], G.nodes[u]['x_coord']], 
                  [G.nodes[v]['y_coord'], G.nodes[v]['x_coord']]]
    
    # Set edge color and style based on road type
    if data['type'] == 'highway':
        color = 'red'
        weight = 4
    elif data['type'] == 'major_road':
        color = 'blue'
        weight = 3
    elif data['type'] == 'minor_road':
        color = 'gray'
        weight = 2
    elif data['type'] == 'potential_road':
        color = 'green'
        weight = 2
        dash_array = '10,10'
    else:
        color = 'purple'
        weight = 1
    
    # Create popup content for the road
    popup_content = f"""
    <div>
        <b>Road Type:</b> {data['type']}<br>
        <b>Status:</b> {data['status']}<br>
        <b>Capacity:</b> {data['capacity']} vehicles/hour<br>
        <b>Condition:</b> {data['condition']}/10
    </div>
    """
    
    # Add the road line to the map
    folium.PolyLine(
        coordinates,
        weight=weight,
        color=color,
        popup=popup_content,
        dash_array='10,10' if data['type'] == 'potential_road' else None,
        opacity=0.8
    ).add_to(m)

# Add a layer control
folium.LayerControl().add_to(m)

# Save the interactive map
map_path = os.path.join(output_dir, 'transportation_network_interactive.html')
m.save(map_path)

# Also create the static matplotlib visualization for comparison
# Draw each type of edge
for edge_type, color in edge_colors.items():
    edges = [(u, v) for u, v, d in G.edges(data=True) if d['type'] == edge_type]
    if edges:
        nx.draw_networkx_edges(G, positions, 
                             edgelist=edges, 
                             edge_color=color,
                             style=edge_styles[edge_type],
                             label=edge_type.replace('_', ' ').title(),
                             width=2 if edge_type == 'highway' else 1)

# Add labels 
labels = {n: G.nodes[n]['name'] for n in G.nodes()}
nx.draw_networkx_labels(G, positions, labels=labels, font_size=6)

plt.title('Cairo Transportation Network')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
plt.axis('off')
plt.tight_layout()

# Save the plots in different formats
output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'graphs')
os.makedirs(output_dir, exist_ok=True)

# Save as PNG for web/viewing
png_path = os.path.join(output_dir, 'transportation_network.png')
plt.savefig(png_path, bbox_inches='tight', dpi=300)


plt.show()

print(f"\nSaved network visualizations to:")
print(f"PNG: {png_path}")


# Print basic statistics
print("\nNetwork Statistics:")
print(f"Number of nodes: {G.number_of_nodes()}")
print(f"Number of edges: {G.number_of_edges()}")
print(f"Number of neighborhoods: {len(neighborhood_nodes)}")
print(f"Number of facilities: {len(facility_nodes)}")
print(f"Number of isolated nodes: {len(isolated_nodes)}")
print(f"  - Isolated neighborhoods: {len(isolated_neighborhoods)}")
print(f"  - Isolated facilities: {len(isolated_facilities)}")
print("\nNeighborhood types:", ', '.join(neighborhood_types))
print("Facility types:", ', '.join(facility_types))

# Save network data in JSON format
graph_data = {
    'nodes': [
        {
            'id': n,
            'name': G.nodes[n]['name'],
            'type': G.nodes[n]['type'],
            'category': G.nodes[n]['node_category'],            'x': float(G.nodes[n]['x_coord']),
            'y': float(G.nodes[n]['y_coord'])
        }
        for n in G.nodes()
    ],
    'edges': [
        {
            'source': u,
            'target': v,
            'type': d['type'],
            'weight': d['weight'],
            'status': d.get('status', 'N/A'),
            'capacity': d.get('capacity', 0),
            'condition': d.get('condition', 0)
        }
        for u, v, d in G.edges(data=True)
    ]
}

# Save as JSON
json_path = os.path.join(output_dir, 'transportation_network.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(graph_data, f, indent=2)

print(f"\nSaved network data to JSON: {json_path}")

# Save the graph for future use (in GEXF format which is more compatible)
nx.write_gexf(G, os.path.join(output_dir, 'transportation_network.gexf'))

