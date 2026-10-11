
import os
import traci
import xml.etree.ElementTree as ET

ROOT = r"C:\Ambulance_SUMO_Project"
CONFIG = os.path.join(ROOT, "simulation", "ambulance.sumocfg")
ROUTES = os.path.join(ROOT, "routes", "ambulance.rou.xml")
TEMP_ROUTES = os.path.join(ROOT, "routes", "scenario4_temp.rou.xml")

SIMULATION_END = 700


def main():
    tree = ET.parse(ROUTES)
    root = tree.getroot()

    # Remove old vehicles and flows, preserving route definitions
    for element in list(root):
        if element.tag in ("vehicle", "flow"):
            root.remove(element)

    # Heavy background traffic
    for direction, route in [
        ("forward", "mainRoute"),
        ("reverse", "reverseRoute"),
    ]:
        ET.SubElement(root, "flow", {
            "id": f"heavy_{direction}",
            "type": "DEFAULT_VEHTYPE",
            "route": route,
            "begin": "0",
            "end": "500",
            "period": "2",
            "departLane": "best",
            "departSpeed": "max",
        })

    # Two ambulances
    ET.SubElement(root, "vehicle", {
        "id": "ambulance_forward_test",
        "type": "ambulance",
        "route": "mainRoute",
        "depart": "10",
    })

    ET.SubElement(root, "vehicle", {
        "id": "ambulance_reverse_test",
        "type": "ambulance",
        "route": "reverseRoute",
        "depart": "70",
    })

    tree.write(TEMP_ROUTES, encoding="UTF-8", xml_declaration=True)

    junction_phases = {
        "J1": {"forward": 0, "reverse": 0},
        "J2": {"forward": 2, "reverse": 2},
        "J3": {"forward": 0, "reverse": 0},
    }

    ambulance_routes = {
        "ambulance_forward_test": "forward",
        "ambulance_reverse_test": "reverse",
    }

    departures = {
        "ambulance_forward_test": 10.0,
        "ambulance_reverse_test": 70.0,
    }

    arrivals = {}
    stop_counts = {vehicle_id: 0 for vehicle_id in ambulance_routes}
    previous_speed = {}
    active_preemptions = set()

    sumo_cmd = [
        "sumo-gui", "-c", CONFIG,
        "--route-files", TEMP_ROUTES,
        "--start", "--delay", "100",
        "--end", str(SIMULATION_END),
    ]

    try:
        traci.start(sumo_cmd)
        print("SCENARIO 4: HEAVY TRAFFIC")
        print("Background traffic period: 2 seconds per direction")

        while traci.simulation.getMinExpectedNumber() > 0:
            current_ids = set(traci.vehicle.getIDList())

            # Detect ambulance arrival when it leaves the network
            for vehicle_id in ambulance_routes:
                if vehicle_id not in current_ids and vehicle_id not in arrivals:
                    # Do not count vehicles that have not departed yet
                    if traci.simulation.getTime() >= departures[vehicle_id]:
                        # Check SUMO's arrived-vehicle list for this step
                        if vehicle_id in traci.simulation.getArrivedIDList():
                            arrivals[vehicle_id] = traci.simulation.getTime()
                            print(f"\nARRIVAL: {vehicle_id} at {arrivals[vehicle_id]:.1f}s")
                            print(f"TRAVEL TIME: {arrivals[vehicle_id] - departures[vehicle_id]:.1f}s")

            requested_phases = {}

            for vehicle_id in current_ids:
                if vehicle_id not in ambulance_routes:
                    continue

                direction = ambulance_routes[vehicle_id]
                next_tls = traci.vehicle.getNextTLS(vehicle_id)

                if next_tls:
                    tls_id, link_index, distance, signal_state = next_tls[0]

                    if tls_id in junction_phases and distance < 100:
                        requested_phases[tls_id] = junction_phases[tls_id][direction]

                speed = traci.vehicle.getSpeed(vehicle_id)
                old_speed = previous_speed.get(vehicle_id, speed)

                if old_speed > 0.1 and speed < 0.1:
                    stop_counts[vehicle_id] += 1

                previous_speed[vehicle_id] = speed

            for tls_id, phase in requested_phases.items():
                if traci.trafficlight.getPhase(tls_id) != phase:
                    traci.trafficlight.setPhase(tls_id, phase)
                active_preemptions.add(tls_id)

            for tls_id in list(active_preemptions):
                if tls_id not in requested_phases:
                    traci.trafficlight.setPhaseDuration(tls_id, 0)
                    active_preemptions.remove(tls_id)

            traci.simulationStep()
            sim_time = traci.simulation.getTime()

            if int(sim_time) % 20 == 1:
                print(f"\nTIME {sim_time:.0f}s")
                print(f"Vehicles in network: {len(traci.vehicle.getIDList())}")

                for vehicle_id in ambulance_routes:
                    if vehicle_id in traci.vehicle.getIDList():
                        print(
                            f"{vehicle_id}: road={traci.vehicle.getRoadID(vehicle_id)}, "
                            f"speed={traci.vehicle.getSpeed(vehicle_id):.1f} m/s"
                        )

            # Stop once both ambulances have arrived
            if len(arrivals) == len(ambulance_routes):
                break

    finally:
        if traci.isLoaded():
            traci.close()

    print("\n===== SCENARIO 4 RESULTS =====")
    for vehicle_id, departure in departures.items():
        if vehicle_id in arrivals:
            travel_time = arrivals[vehicle_id] - departure
            print(f"\nAmbulance: {vehicle_id}")
            print(f"Departure: {departure:.1f}s")
            print(f"Arrival: {arrivals[vehicle_id]:.1f}s")
            print(f"Travel time: {travel_time:.1f}s")
            print(f"Stop events: {stop_counts[vehicle_id]}")
        else:
            print(f"\n{vehicle_id}: arrival not recorded")


if __name__ == "__main__":
    main()
