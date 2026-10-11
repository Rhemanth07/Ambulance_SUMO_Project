
import os
import sys
import xml.etree.ElementTree as ET
import traci

SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"
SUMO_GUI = os.path.join(SUMO_HOME, "bin", "sumo-gui.exe")
CONFIG = r"C:\Ambulance_SUMO_Project\simulation\ambulance.sumocfg"
JUNCTIONS = ["J1", "J2", "J3"]
DETECTION_RANGE = 300.0
AMBULANCE_PREFIX = "ambulance"
ROUTE_FILE = r"C:\Ambulance_SUMO_Project\routes\ambulance.rou.xml"
TEMP_ROUTE = r"C:\Ambulance_SUMO_Project\routes\scenario_temp.rou.xml"

SCENARIO = int(sys.argv[1]) if len(sys.argv) > 1 else 1

def get_ambulance_junction(road_id):
    forward_roads = {
        "E0": "J1",
        "E1": "J2",
        "E2": "J3",
    }

    reverse_roads = {
        "-E9": "J3",
        "-E2": "J2",
        "-E1": "J1",
    }

    return forward_roads.get(
        road_id,
        reverse_roads.get(road_id)
    )


def find_approaching_ambulances(ambulances):
    approaching = []

    for ambulance_id in ambulances:
        road_id = traci.vehicle.getRoadID(ambulance_id)
        junction = get_ambulance_junction(road_id)

        if junction is None:
            continue

        position = traci.vehicle.getPosition(ambulance_id)
        junction_position = traci.junction.getPosition(junction)

        distance = (
            (position[0] - junction_position[0]) ** 2
            + (position[1] - junction_position[1]) ** 2
        ) ** 0.5

        if distance <= DETECTION_RANGE:
            approaching.append(
                (ambulance_id, junction, distance, road_id)
            )

    return approaching


def get_priority_phase(junction, road_id):
    forward_phases = {
        "J1": 0,
        "J2": 2,
        "J3": 0,
    }

    reverse_phases = {
        "J1": 2,
        "J2": 0,
        "J3": 2,
    }

    if road_id in ("E0", "E1", "E2"):
        return forward_phases.get(junction)

    if road_id in ("-E9", "-E2", "-E1"):
        return reverse_phases.get(junction)

    return None


def create_scenario_routes():
    tree = ET.parse(ROUTE_FILE)
    root = tree.getroot()

    # Remove original ambulance vehicles and ambulance flows.
    for item in list(root):
        if item.tag == "vehicle" and (
            item.get("type") == "ambulance"
            or item.get("id", "").startswith("ambulance")
        ):
            root.remove(item)
        elif item.tag == "flow" and item.get("type") == "ambulance":
            root.remove(item)

    if SCENARIO == 1:
        print("SCENARIO 1: NORMAL TRAFFIC - ZERO AMBULANCES")

    elif SCENARIO == 2:
        # Repeated arrivals in the same direction.
        ET.SubElement(root, "flow", {
            "id": "ambulance_same",
            "type": "ambulance",
            "route": "mainRoute",
            "begin": "0",
            "end": "600",
            "period": "30"
        })
        print("SCENARIO 2: SAME-DIRECTION AMBULANCES EVERY 30 SECONDS")

    elif SCENARIO == 3:
        # Repeated arrivals from opposite ends.
        ET.SubElement(root, "flow", {
            "id": "ambulance_forward",
            "type": "ambulance",
            "route": "mainRoute",
            "begin": "0",
            "end": "600",
            "period": "30"
        })
        ET.SubElement(root, "flow", {
            "id": "ambulance_reverse",
            "type": "ambulance",
            "route": "reverseRoute",
            "begin": "15",
            "end": "600",
            "period": "30"
        })
        print("SCENARIO 3: OPPOSITE-DIRECTION AMBULANCES")
        print("Forward arrivals: 0, 30, 60... seconds")
        print("Reverse arrivals: 15, 45, 75... seconds")

    else:
        raise ValueError("Choose scenario 1, 2, or 3.")

    # Keep vehicle types and routes before traffic definitions.
    route_defs = [
        e for e in root if e.tag in ("vType", "route")
    ]
    other_defs = [
        e for e in root
        if e.tag not in ("vType", "route", "vehicle", "flow")
    ]
    traffic = [
        e for e in root if e.tag in ("vehicle", "flow")
    ]

    def departure_time(e):
        return float(e.get("depart", e.get("begin", "0")))

    traffic.sort(key=departure_time)
    root[:] = route_defs + other_defs + traffic

    tree.write(
        TEMP_ROUTE,
        encoding="UTF-8",
        xml_declaration=True
    )

def main():
    create_scenario_routes()

    traci.start([
        SUMO_GUI, "-c", CONFIG,
        "--route-files", TEMP_ROUTE,
        "--start", "--delay", "300"
    ])

    priority_requests = {}

    try:
        print(f"SCENARIO {SCENARIO} STARTED")

        last_report_time = -10

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()

            vehicles = traci.vehicle.getIDList()
            ambulances = [
                v for v in vehicles
                if v.startswith("ambulance")
            ]
           
            approaching = find_approaching_ambulances(ambulances)

            for ambulance_id, junction, distance, road_id in approaching:
                print(
                    f"AMBULANCE DETECTED: {ambulance_id} | "
                    f"Junction: {junction} | "
                    f"Distance: {distance:.1f} m | "
                    f"Road: {road_id}"
                )
            
                phase = get_priority_phase(junction, road_id)

                if phase is not None:
                    priority_requests[ambulance_id] = {
                        "junction": junction,
                        "phase": phase,
                        "distance": distance,
                    }

            sim_time = int(traci.simulation.getTime())

            if sim_time - last_report_time >= 10:
                print(
                    f"TIME {sim_time}s | "
                    f"Vehicles: {len(vehicles)} | "
                    f"Ambulances present: {len(ambulances)}"
                )

                for ambulance_id in ambulances:
                    print(
                        f"  {ambulance_id}: "
                        f"road={traci.vehicle.getRoadID(ambulance_id)}, "
                        f"speed={traci.vehicle.getSpeed(ambulance_id):.1f} m/s"
                    )

                last_report_time = sim_time
    finally:
        traci.close()

if __name__ == "__main__":
    main()
