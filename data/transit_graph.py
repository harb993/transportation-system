import json
import networkx as nx
import matplotlib.pyplot as plt
import os
from math import sqrt
import folium
import datetime
from collections import defaultdict

def load_json_data(filename):
    """Load and return JSON data from a file"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points"""
    return sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def create_transit_graph():
    """Create a transit graph with metro lines and bus routes"""
    # Load transit and facilities data
    data_dir = os.path.dirname(__file__)
    transit_path = os.path.join(data_dir, 'transit_data.json')
    facilities_path = os.path.join(data_dir, 'facilities.json')
    
    transit_data = load_json_data(transit_path)
    facilities_data = load_json_data(facilities_path)
    
    # Create directed graph for transit routes
    G = nx.MultiDiGraph()

    # Create a mapping of numerical IDs to neighborhood IDs
    node_mapping = {}
    for i, node in enumerate(facilities_data['neighborhoods'], 1):
        node_id = str(i)  # Transit data uses string numbers as IDs
        node_mapping[node_id] = node['ID']
        G.add_node(
            node_id,  # Use the numeric ID to match transit data
            name=node['Name'],
            type='station',
            population=0,  # We don't have population data in this example
            pos=(node['X_coordinate'], node['Y_coordinate'])
        )

    # Add facility nodes - these keep their original IDs as they're referenced directly
    for facility in facilities_data['facilities']:
        G.add_node(
            facility['ID'],
            name=facility['Name'],
            type='facility',
            pos=(facility['X_coordinate'], facility['Y_coordinate']),
            facility_type=facility['Type']
        )

    # Add metro lines
    for line in transit_data['metro_lines']:
        stations = line['Stations_comma_separated_IDs']
        for i in range(len(stations) - 1):
            current_node = stations[i]
            next_node = stations[i + 1]
            if not G.has_node(current_node) or not G.has_node(next_node):
                print(f"Warning: Skipping metro edge {current_node}-{next_node} - one or both nodes missing")
                continue
            G.add_edge(
                current_node, next_node, type='metro',
                line_id=line['LineID'], passengers=line['Daily_Passengers']
            )
            G.add_edge(
                next_node, current_node, type='metro',
                line_id=line['LineID'], passengers=line['Daily_Passengers']
            )

    # Add bus routes
    for route in transit_data['bus_routes']:
        stops = route['Stops_comma_separated_IDs']
        for i in range(len(stops) - 1):
            current_node = stops[i]
            next_node = stops[i + 1]
            if not G.has_node(current_node) or not G.has_node(next_node):
                print(f"Warning: Skipping bus edge {current_node}-{next_node} - one or both nodes missing")
                continue
            G.add_edge(
                current_node, next_node, type='bus',
                route_id=route['RouteID'], passengers=route['Daily_Passengers'],
                buses=route['Buses_Assigned']
            )

    return G

def visualize_transit_graph(G):
    """Visualize the transit graph statically and interactively"""
    # Create interactive map
    m = create_interactive_transit_map(G)
    
    # Save the interactive map
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'graphs')
    os.makedirs(output_dir, exist_ok=True)
    map_path = os.path.join(output_dir, 'transit_network_interactive.html')
    m.save(map_path)
    
    # Create static visualization
    plt.figure(figsize=(15, 10))
    
    pos = nx.get_node_attributes(G, 'pos')
    nodes_with_pos = list(pos.keys())
    
    stations = [n for n in nodes_with_pos if G.nodes[n]['type'] == 'station']
    facilities = [n for n in nodes_with_pos if G.nodes[n]['type'] == 'facility']
    
    if stations:
        populations = [G.nodes[n].get('population', 0) for n in stations]
        node_sizes = [max(100, min(1000, pop/5000)) for pop in populations]
        nx.draw_networkx_nodes(G, pos, nodelist=stations, 
                             node_color='lightgray', node_size=node_sizes,
                             label='Stations')
    
    if facilities:
        facility_types = [G.nodes[n].get('facility_type', 'Other') for n in facilities]
        facility_colors = {
            'Residential': 'green', 'Business': 'blue', 'Mixed': 'purple',
            'Medical': 'red', 'Education': 'orange', 'Airport': 'cyan',
            'Transit Hub': 'brown', 'Tourism': 'pink', 'Sports': 'gray',
            'Commercial': 'yellow', 'Other': 'black'
        }
        facility_node_colors = [facility_colors.get(t, 'black') for t in facility_types]
        nx.draw_networkx_nodes(G, pos, nodelist=facilities,
                             node_color=facility_node_colors, node_size=200,
                             node_shape='s', label='Facilities')
    
    metro_colors = {'M1': 'red', 'M2': 'blue', 'M3': 'green'}
    for line_id, color in metro_colors.items():
        line_edges = [(u, v) for u, v, d in G.edges(data=True) 
                     if d.get('type') == 'metro' and d.get('line_id') == line_id
                     and u in pos and v in pos]
        if line_edges:
            edge_weights = [max(2, min(7, G.edges[u, v, 0]['passengers']/300000)) 
                          for u, v in line_edges]
            nx.draw_networkx_edges(G, pos, edgelist=line_edges,
                                 edge_color=color, width=edge_weights,
                                 label=f'Metro {line_id}')
    
    bus_edges = [(u, v) for u, v, d in G.edges(data=True) 
                 if d.get('type') == 'bus' and u in pos and v in pos]
    if bus_edges:
        bus_weights = []
        for u, v in bus_edges:
            # Find the bus edge data among multiple edges
            edge_data = None
            for _, _, data in G.edges(data=True):
                if data.get('type') == 'bus' and \
                   G.has_edge(u, v) and \
                   data.get('buses') is not None:
                    edge_data = data
                    break

            if edge_data:
                weight = max(1.5, min(5, edge_data['buses']/10))
                bus_weights.append(weight)
            else:
                bus_weights.append(2.0)  # Default weight if no bus data found
        
        nx.draw_networkx_edges(G, pos, edgelist=bus_edges,
                             edge_color='orange', style='dashed',
                             width=bus_weights, label='Bus Routes')
    
    labels = {
        node: f"{G.nodes[node]['name']}\n({G.nodes[node].get('population', 0):,})"
        if G.nodes[node]['type'] == 'station' and G.nodes[node].get('population', 0) > 300000
        else G.nodes[node]['name']
        for node in nodes_with_pos
        if G.nodes[node]['type'] == 'facility' or
           (G.nodes[node]['type'] == 'station' and G.nodes[node].get('population', 0) > 300000)
    }
    if labels:
        nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    plt.title('Cairo Public Transit Network\nMetro Lines and Bus Routes\n'
             'Node size: Population | Edge width: Passenger volume',
             pad=20)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.axis('off')
    plt.tight_layout()
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'graphs')
    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, 'transit_network.png')
    plt.savefig(png_path, bbox_inches='tight', dpi=300)
    
    # Calculate and print detailed statistics
    nodes_without_pos = [n for n in G.nodes() if n not in pos]
    isolated_nodes = [n for n in G.nodes() if G.degree(n) == 0]
    
    print("\n=== Cairo Transit Network Statistics ===")
    print(f"\nVisualization files saved to:")
    print(f"Interactive Map: {map_path}")
    print(f"Static PNG: {png_path}")
    
    print("\nNode Statistics:")
    print(f"Total Stations: {len(stations)}")
    print(f"Total Facilities: {len(facilities)}")
    print(f"Isolated Nodes: {len(isolated_nodes)}")
    if isolated_nodes:
        print("Isolated Nodes:", ', '.join(isolated_nodes))
    
    total_population = sum(G.nodes[n].get('population', 0) for n in stations)
    print(f"\nPopulation Statistics:")
    print(f"Total Population Served: {total_population:,}")
    
    major_stations = [(n, G.nodes[n]) for n in stations 
                     if G.nodes[n].get('population', 0) > 300000]
    if major_stations:
        print(f"\nMajor Stations (>300k population):")
        for node, data in sorted(major_stations, 
                               key=lambda x: x[1].get('population', 0), 
                               reverse=True):
            print(f"  - {data['name']}: {data['population']:,} residents")
    
    facility_counts = defaultdict(int)
    for f in facilities:
        f_type = G.nodes[f].get('facility_type', 'Other')
        facility_counts[f_type] += 1
    
    print("\nFacility Types:")
    for f_type, count in sorted(facility_counts.items()):
        print(f"  - {f_type}: {count}")
    
    metro_lines = set(d['line_id'] for _, _, d in G.edges(data=True) 
                     if d.get('type') == 'metro')
    bus_routes = set(d['route_id'] for _, _, d in G.edges(data=True) 
                    if d.get('type') == 'bus')
    
    print("\nTransit Line Statistics:")
    print(f"Metro Lines: {len(metro_lines)}")
    
    print("\nMetro Line Details:")
    for line in sorted(metro_lines):
        line_edges = [(u, v, d) for u, v, d in G.edges(data=True)
                     if d.get('type') == 'metro' and d.get('line_id') == line]
        passengers = sum(d['passengers'] for _, _, d in line_edges) // 2  # Halve for bidirectional
        stations_served = len(set([u for u, _, _ in line_edges] + 
                               [v for _, v, _ in line_edges]))
        print(f"  - {line}: {passengers:,} daily passengers, {stations_served} stations")
    
    print(f"\nBus Routes: {len(bus_routes)}")
    
    total_buses = sum(d['buses'] for _, _, d in G.edges(data=True)
                     if d.get('type') == 'bus')
    print(f"Total Buses in Service: {total_buses}")
    
    metro_passengers = sum(d['passengers'] for _, _, d in G.edges(data=True)
                         if d.get('type') == 'metro') // 2  # Halve for bidirectional
    bus_passengers = sum(d['passengers'] for _, _, d in G.edges(data=True)
                        if d.get('type') == 'bus')
    total_passengers = metro_passengers + bus_passengers
    
    print("\nDaily Passenger Statistics:")
    if total_passengers > 0:
        print(f"Metro Passengers: {metro_passengers:,} ({metro_passengers/total_passengers*100:.1f}%)")
        print(f"Bus Passengers: {bus_passengers:,} ({bus_passengers/total_passengers*100:.1f}%)")
        print(f"Total Passengers: {total_passengers:,}")
    else:
        print("No passenger data available")
    
    print("\nEfficiency Metrics:")
    if len(metro_lines) > 0:
        print(f"Average Passengers per Metro Line: {metro_passengers // len(metro_lines):,}")
    if len(bus_routes) > 0:
        print(f"Average Passengers per Bus Route: {bus_passengers // len(bus_routes):,}")
    if total_buses > 0:
        print(f"Average Daily Passengers per Bus: {bus_passengers // total_buses:,}")
    
    print("\nNetwork Connectivity:")
    print(f"Total Network Nodes: {G.number_of_nodes()}")
    print(f"Total Network Edges: {G.number_of_edges()}")
    avg_degree = sum(dict(G.degree()).values()) / G.number_of_nodes()
    print(f"Average Node Degree: {avg_degree:.2f}")
    
    stats_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'reports')
    os.makedirs(stats_dir, exist_ok=True)
    stats_file = os.path.join(stats_dir, 'transit_network_statistics.txt')
    
    with open(stats_file, 'w') as f:
        f.write("Cairo Transit Network Statistics\n")
        f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Network Summary:\n")
        f.write(f"- Total Stations: {len(stations)}\n")
        f.write(f"- Total Facilities: {len(facilities)}\n")
        f.write(f"- Isolated Nodes: {len(isolated_nodes)}\n")
        f.write(f"- Total Population Served: {total_population:,}\n")
        if total_passengers > 0:
            f.write(f"- Daily Passengers: {total_passengers:,}\n")
            f.write(f"  * Metro: {metro_passengers:,}\n")
            f.write(f"  * Bus: {bus_passengers:,}\n")
        else:
            f.write("- No passenger data available\n")
        f.write(f"\nTransit Infrastructure:\n")
        f.write(f"- Metro Lines: {len(metro_lines)}\n")
        f.write(f"- Bus Routes: {len(bus_routes)}\n")
        f.write(f"- Total Buses: {total_buses}\n")
    
    print(f"\nDetailed statistics saved to: {stats_file}")

def create_interactive_transit_map(G):
    """Create an interactive map of the transit network using Folium"""
    # Create map centered on Cairo
    cairo_center = [30.05, 31.25]  # Lat, Lon
    m = folium.Map(location=cairo_center, zoom_start=11)
    
    # Add stations and facilities
    for node, data in G.nodes(data=True):
        if 'pos' not in data:
            print(f"Warning: Node {node} has no position data, skipping...")
            continue
        # Note: pos=(x,y) where x=longitude, y=latitude; Folium uses [lat, lon]
        pos = data['pos']
        location = [pos[1], pos[0]]
        
        if data['type'] == 'station':
            popup_content = f"""
            <div style='min-width: 200px'>
                <h4>{data['name']}</h4>
                <b>Type:</b> Transit Station<br>
                <b>Population Served:</b> {data.get('population', 'N/A'):,}<br>
                <b>ID:</b> {node}
            </div>
            """
            folium.CircleMarker(
                location=location,
                radius=6,
                popup=folium.Popup(popup_content, max_width=300),
                color='gray',
                fill=True,
                fillColor='lightgray',
                fillOpacity=0.7,
                weight=2
            ).add_to(m)
        else:  # facility
            facility_type = data.get('facility_type', 'Other')
            popup_content = f"""
            <div style='min-width: 200px'>
                <h4>{data['name']}</h4>
                <b>Type:</b> {facility_type}<br>
                <b>ID:</b> {node}
            </div>
            """
            icon = 'plus' if facility_type == 'Medical' else (
                   'graduation-cap' if facility_type == 'Education' else (
                   'plane' if facility_type == 'Airport' else (
                   'building' if facility_type == 'Business' else (
                   'shopping-cart' if facility_type == 'Commercial' else (
                   'home' if facility_type == 'Residential' else (
                   'train' if facility_type == 'Transit Hub' else (
                   'camera' if facility_type == 'Tourism' else (
                   'futbol-o' if facility_type == 'Sports' else 'star'))))))))
            
            folium.Marker(
                location=location,
                popup=folium.Popup(popup_content, max_width=300),
                icon=folium.Icon(color='red', icon=icon, prefix='fa'),
                tooltip=data['name']
            ).add_to(m)
    
    # Add transit lines
    metro_colors = {'M1': 'red', 'M2': 'blue', 'M3': 'green'}
    
    for line_id, color in metro_colors.items():
        edges = [(u, v, d) for u, v, d in G.edges(data=True) 
                if d.get('type') == 'metro' and d.get('line_id') == line_id]
        for u, v, data in edges:
            if 'pos' not in G.nodes[u] or 'pos' not in G.nodes[v]:
                print(f"Warning: Metro edge between {u} and {v} skipped - missing position data")
                continue
            coordinates = [
                [G.nodes[u]['pos'][1], G.nodes[u]['pos'][0]],
                [G.nodes[v]['pos'][1], G.nodes[v]['pos'][0]]
            ]
            popup_content = f"""
            <div>
                <b>Metro Line:</b> {line_id}<br>
                <b>Daily Passengers:</b> {data['passengers']:,}
            </div>
            """
            folium.PolyLine(
                coordinates,
                weight=4,
                color=color,
                popup=popup_content,
                opacity=0.8
            ).add_to(m)
    
    bus_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get('type') == 'bus']
    for u, v, data in bus_edges:
        if 'pos' not in G.nodes[u] or 'pos' not in G.nodes[v]:
            print(f"Warning: Bus edge between {u} and {v} skipped - missing position data")
            continue
        coordinates = [
            [G.nodes[u]['pos'][1], G.nodes[u]['pos'][0]],
            [G.nodes[v]['pos'][1], G.nodes[v]['pos'][0]]
        ]
        popup_content = f"""
        <div>
            <b>Bus Route:</b> {data['route_id']}<br>
            <b>Daily Passengers:</b> {data['passengers']:,}<br>
            <b>Buses Assigned:</b> {data['buses']}
        </div>
        """
        folium.PolyLine(        coordinates,
            weight=4,
            color='black',
            popup=popup_content,
            opacity=0.6,
            dash_array='10,10'
        ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    return m

if __name__ == "__main__":
    # Create and visualize the transit graph
    G = create_transit_graph()
    visualize_transit_graph(G)
    print("\nSaved interactive transit map to: ../output/graphs/transit_network_interactive.html")