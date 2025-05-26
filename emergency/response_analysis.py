import json
import statistics

# --- Data Loading (Shared logic - consider a common utility) ---
def load_json_data(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Data file not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None

# --- Emergency Response Analysis ---
def analyze_emergency_response_times(simulation_history):
    """
    Analyzes response times from emergency simulation history.
    Args:
        simulation_history (list): A list of states from the EmergencySimulator.
    Returns:
        dict: Analysis results including average response times, etc.
    """
    if not simulation_history:
        return {"error": "Simulation history is empty."}

    dispatch_times = [] # Time from incident report to vehicle assignment
    arrival_at_incident_times = [] # Time from assignment to arrival at incident
    arrival_at_facility_times = [] # Time from incident pickup to arrival at facility
    total_resolution_times = [] # Time from incident report to arrival at facility

    # Track incidents to calculate durations
    incident_timings = {}
    # incident_timings[incident_id] = {
    # "reported_step": step,
    # "assigned_step": step,
    # "vehicle_arrived_incident_step": step,
    # "vehicle_arrived_facility_step": step
    # }

    for step_data in simulation_history:
        step = step_data["step"]
        
        # Track incident reporting and assignment
        for incident_sim in step_data.get("incidents", []):
            inc_id = incident_sim["id"]
            if inc_id not in incident_timings:
                incident_timings[inc_id] = {"reported_step": step, "location": incident_sim["location"]}
            
            if incident_sim.get("status") == "vehicle_assigned" and "assigned_step" not in incident_timings[inc_id]:
                incident_timings[inc_id]["assigned_step"] = step
                incident_timings[inc_id]["assigned_vehicle"] = incident_sim["assigned_vehicle"]
                dispatch_time = step - incident_timings[inc_id]["reported_step"]
                dispatch_times.append(dispatch_time)

        # Track vehicle movements and arrivals
        for vehicle_sim in step_data.get("vehicles", []):
            veh_id = vehicle_sim["id"]
            # Find incidents this vehicle was assigned to
            for inc_id, inc_data in incident_timings.items():
                if inc_data.get("assigned_vehicle") == veh_id:
                    # Vehicle arrived at incident
                    if vehicle_sim["current_node"] == inc_data["location"] and \
                       vehicle_sim["status"] == "enroute_to_facility" and \
                       "vehicle_arrived_incident_step" not in inc_data:
                        inc_data["vehicle_arrived_incident_step"] = step
                        if "assigned_step" in inc_data:
                            time_to_incident = step - inc_data["assigned_step"]
                            arrival_at_incident_times.append(time_to_incident)
                    
                    # Vehicle arrived at facility with payload
                    if vehicle_sim["status"] == "at_facility" and \
                       vehicle_sim["current_node"] == vehicle_sim["facility_target"] and \
                       "vehicle_arrived_facility_step" not in inc_data and \
                       inc_data.get("vehicle_arrived_incident_step") is not None: # Ensure patient was picked up
                        inc_data["vehicle_arrived_facility_step"] = step
                        time_to_facility = step - inc_data["vehicle_arrived_incident_step"]
                        arrival_at_facility_times.append(time_to_facility)
                        
                        total_time = step - inc_data["reported_step"]
                        total_resolution_times.append(total_time)
                        inc_data["resolved_step"] = step # Mark as fully resolved for timing
                        break # Vehicle handled one incident fully
    
    # Post-process incident_timings for any unresolved or partially resolved incidents if needed
    # For now, we only count fully completed cycles for robust timing.

    analysis = {
        "num_incidents_processed_for_timing": len(total_resolution_times),
        "dispatch_times_steps": dispatch_times,
        "arrival_at_incident_times_steps": arrival_at_incident_times,
        "arrival_at_facility_times_steps": arrival_at_facility_times,
        "total_resolution_times_steps": total_resolution_times,
        "avg_dispatch_time_steps": statistics.mean(dispatch_times) if dispatch_times else None,
        "median_dispatch_time_steps": statistics.median(dispatch_times) if dispatch_times else None,
        "avg_arrival_at_incident_time_steps": statistics.mean(arrival_at_incident_times) if arrival_at_incident_times else None,
        "median_arrival_at_incident_time_steps": statistics.median(arrival_at_incident_times) if arrival_at_incident_times else None,
        "avg_arrival_at_facility_time_steps": statistics.mean(arrival_at_facility_times) if arrival_at_facility_times else None,
        "median_arrival_at_facility_time_steps": statistics.median(arrival_at_facility_times) if arrival_at_facility_times else None,
        "avg_total_resolution_time_steps": statistics.mean(total_resolution_times) if total_resolution_times else None,
        "median_total_resolution_time_steps": statistics.median(total_resolution_times) if total_resolution_times else None,
        "incident_details_timed": incident_timings
    }
    return analysis

if __name__ == "__main__":
    print("Testing Emergency Response Analysis")
    # This script expects a simulation history file (e.g., JSON) as input.
    # For testing, we would normally load a history file generated by emergency_simulation.py.
    # Since we can't run the full simulation here to generate a live file easily,
    # we will assume a conceptual history or load a pre-saved one if available.

    # Path to a potential simulation history file (replace with actual path if you save history from simulation)
    history_file_path = "/home/ubuntu/transportation_system/output/emergency_sim_history.json"

    # Conceptual: If emergency_simulation.py saved its history to a JSON file:
    # sim_history = load_json_data(history_file_path)

    # For this standalone test, let's create a small, dummy simulation history:
    dummy_history = [
        {"step": 0, "time_of_day": "morning_peak", "incidents": [{"id": "INC0_0", "location": "N1", "status": "pending_dispatch"}], "vehicles": [{"id": "EV0", "current_node": "H1", "status": "available"}]},
        {"step": 1, "time_of_day": "morning_peak", "incidents": [{"id": "INC0_0", "location": "N1", "status": "vehicle_assigned", "assigned_vehicle": "EV0"}], "vehicles": [{"id": "EV0", "current_node": "H1", "status": "enroute_to_incident", "incident_target": "N1"}]},
        {"step": 2, "time_of_day": "morning_peak", "incidents": [{"id": "INC0_0", "location": "N1", "status": "vehicle_assigned", "assigned_vehicle": "EV0"}], "vehicles": [{"id": "EV0", "current_node": "N1", "status": "enroute_to_facility", "incident_target": "N1", "facility_target": "H1", "payload": True}]},
        {"step": 3, "time_of_day": "afternoon",    "incidents": [], "vehicles": [{"id": "EV0", "current_node": "H1", "status": "at_facility", "facility_target": "H1", "payload": False}]},
        {"step": 4, "time_of_day": "afternoon",    "incidents": [], "vehicles": [{"id": "EV0", "current_node": "H1", "status": "available"}]},
        # Another incident
        {"step": 5, "time_of_day": "evening_peak", "incidents": [{"id": "INC5_1", "location": "N2", "status": "pending_dispatch"}], "vehicles": [{"id": "EV0", "current_node": "H1", "status": "available"}]},
        {"step": 6, "time_of_day": "evening_peak", "incidents": [{"id": "INC5_1", "location": "N2", "status": "vehicle_assigned", "assigned_vehicle": "EV0"}], "vehicles": [{"id": "EV0", "current_node": "H1", "status": "enroute_to_incident", "incident_target": "N2"}]},
        {"step": 7, "time_of_day": "evening_peak", "incidents": [{"id": "INC5_1", "location": "N2", "status": "vehicle_assigned", "assigned_vehicle": "EV0"}], "vehicles": [{"id": "EV0", "current_node": "N2", "status": "enroute_to_facility", "incident_target": "N2", "facility_target": "H1", "payload": True}]},
        {"step": 8, "time_of_day": "night",        "incidents": [], "vehicles": [{"id": "EV0", "current_node": "H1", "status": "at_facility", "facility_target": "H1", "payload": False}]},
    ]

    # Save dummy history to a file to simulate loading (optional)
    # with open(history_file_path, "w") as f_hist:
    #     json.dump(dummy_history, f_hist, indent=4)
    # sim_history_loaded = load_json_data(history_file_path)

    sim_history_to_analyze = dummy_history # Use dummy history directly for this test

    if sim_history_to_analyze:
        print(f"Analyzing simulation history with {len(sim_history_to_analyze)} steps.")
        analysis_results = analyze_emergency_response_times(sim_history_to_analyze)

        if "error" in analysis_results:
            print(f"Analysis Error: {analysis_results["error"]}")
        else:
            print("\n--- Emergency Response Analysis Results ---")
            print(f"Number of Incidents Fully Timed: {analysis_results["num_incidents_processed_for_timing"]}")
            print(f"Average Dispatch Time: {analysis_results["avg_dispatch_time_steps"]} steps")
            print(f"Median Dispatch Time: {analysis_results["median_dispatch_time_steps"]} steps")
            print(f"Average Time to Incident (from dispatch): {analysis_results["avg_arrival_at_incident_time_steps"]} steps")
            print(f"Median Time to Incident (from dispatch): {analysis_results["median_arrival_at_incident_time_steps"]} steps")
            print(f"Average Time to Facility (from incident): {analysis_results["avg_arrival_at_facility_time_steps"]} steps")
            print(f"Median Time to Facility (from incident): {analysis_results["median_arrival_at_facility_time_steps"]} steps")
            print(f"Average Total Resolution Time (report to facility): {analysis_results["avg_total_resolution_time_steps"]} steps")
            print(f"Median Total Resolution Time (report to facility): {analysis_results["median_total_resolution_time_steps"]} steps")
            
            # print("\nIncident Timing Details:")
            # for inc_id, timings in analysis_results["incident_details_timed"].items():
            #     print(f"  Incident {inc_id}: {timings}")
    else:
        print(f"Could not load or use simulation history from {history_file_path} (or dummy history failed).")

