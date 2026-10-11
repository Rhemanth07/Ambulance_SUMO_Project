
import os
import sys
import xml.etree.ElementTree as ET
import traci

SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"
SUMO_GUI = os.path.join(SUMO_HOME, "bin", "sumo-gui.exe")
CONFIG = r"C:\Ambulance_SUMO_Project\simulation\ambulance.sumocfg"
ROUTE_FILE = r"C:\Ambulance_SUMO_Project\routes\ambulance.rou.xml"
TEMP_ROUTE = r"C:\Ambulance_SUMO_Project\routes\scenario_temp.rou.xml"

JUNCTIONS = ["J1", "J2", "J3"]
DETECTION_RANGE = 300.0
SIMULATION_END = 600
SCENARIO = int(sys.argv[1]) if len(sys.argv) > 1 else 1

# Existing green phases verified in your SUMO network.
FORWARD_PHASE = {"J1": 0, "J2": 2, "J3": 0}
REVERSE_PHASE = {"J1": 2, "J2": 0, "J3": 2}

# Yellow phase that follows each existing green phase.
YELLOW_AFTER_GREEN = {
    "J1": {0: 1, 2: 3},
    "J2": {0: 1, 2: 3},
    "J3": {0: 1, 2: 3},
}

FORWARD_ROADS = {"E0": "J1", "E1": "J2", "E2": "J3"}
REVERSE_ROADS = {"-E9": "J3", "-E2": "J2", "-E1": "J1"}


def get_approach(road_id):
    if road_id in FORWARD_ROADS:
        return FORWARD_ROADS[road_id], FORWARD_PHASE[FORWARD_ROADS[road_id]]

    if road_id in REVERSE_ROADS:
        return REVERSE_ROADS[road_id], REVERSE_PHASE[REVERSE_ROADS[road_id]]

    return None, None


def create_scenario_routes():
    tree = ET.parse(ROUTE_FILE)
    root = tree.getroot()

    # Remove original ambulance vehicles/flows from the temporary copy.
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
        ET.SubElement(root, "flow", {
            "id": "ambulance_same",
            "type": "ambulance",
            "route": "mainRoute",
            "begin": "0",
            "end": str(SIMULATION_END),
            "period": "120",
        })
        print("SCENARIO 2: SAME-DIRECTION AMBULANCES EVERY 30 SECONDS")

    
    elif SCENARIO == 3:
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
        print("SCENARIO 3: TWO AMBULANCES ONLY")
        print("Forward ambulance departs at 10 seconds")
        print("Reverse ambulance departs at 70 seconds")

    else:
        raise ValueError("Choose scenario 1, 2, or 3.")

    # Keep route and vehicle-type definitions before vehicle/flow entries.
    definitions = [
        item for item in root if item.tag in ("vType", "route")
    ]
    other = [
        item for item in root
        if item.tag not in ("vType", "route", "vehicle", "flow")
    ]
    traffic = [
        item for item in root if item.tag in ("vehicle", "flow")
    ]
    traffic.sort(
        key=lambda item: float(item.get("depart", item.get("begin", "0")))
    )
    root[:] = definitions + other + traffic

    tree.write(TEMP_ROUTE, encoding="UTF-8", xml_declaration=True)


def main():
    create_scenario_routes()

    traci.start([
        SUMO_GUI, "-c", CONFIG,
        "--route-files", TEMP_ROUTE,
        "--start", "--delay", "300",
    ])

    # junction -> (target phase, simulation time when yellow ends)
    transitions = {}
    last_report_time = -10
    last_detection_log = {}

    try:
        print(f"SCENARIO {SCENARIO} STARTED")
        print("Ambulance detection and signal-priority prototype active")

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            sim_time = traci.simulation.getTime()

            vehicles = traci.vehicle.getIDList()
            ambulances = [
                vid for vid in vehicles
                if vid.startswith("ambulance")
            ]

            # Find the nearest detected ambulance for each junction.
            requests = {}

            for ambulance_id in ambulances:
                road_id = traci.vehicle.getRoadID(ambulance_id)
                junction, target_phase = get_approach(road_id)

                if junction is None:
                    continue

                position = traci.vehicle.getPosition(ambulance_id)
                jpos = traci.junction.getPosition(junction)
                distance = (
                    (position[0] - jpos[0]) ** 2
                    + (position[1] - jpos[1]) ** 2
                ) ** 0.5

                if distance > DETECTION_RANGE:
                    continue

                current = requests.get(junction)
                if current is None or distance < current[2]:
                    requests[junction] = (
                        ambulance_id, target_phase, distance, road_id
                    )

                log_key = (ambulance_id, junction)
                if sim_time - last_detection_log.get(log_key, -10) >= 10:
                    print(
                        f"AMBULANCE DETECTED: {ambulance_id} | "
                        f"{junction} | {distance:.1f} m | {road_id}"
                    )
                    last_detection_log[log_key] = sim_time

            for junction in JUNCTIONS:
                request = requests.get(junction)

                # Finish a yellow transition already started.
                if junction in transitions:
                    target_phase, ready_time = transitions[junction]

                    if sim_time >= ready_time:
                        traci.trafficlight.setPhase(junction, target_phase)
                        traci.trafficlight.setPhaseDuration(junction, 2.0)
                        print(
                            f"PRIORITY GREEN: {junction} "
                            f"phase {target_phase} | "
                            f"actual phase={traci.trafficlight.getPhase(junction)} | "
                            f"signal={traci.trafficlight.getRedYellowGreenState(junction)}"
                        )
                        print("J3 LINKS:", traci.trafficlight.getControlledLinks("J3"))
                        del transitions[junction]

                    continue

                if request is None:
                    continue

                ambulance_id, target_phase, distance, road_id = request
                current_phase = traci.trafficlight.getPhase(junction)
                if junction == "J3":
                    print(
                        f"J3 DEBUG: ambulance={ambulance_id}, "
                        f"road={road_id}, target={target_phase}, "
                        f"current_phase={current_phase}"
                    )

                if current_phase == target_phase:
                    traci.trafficlight.setPhaseDuration(junction, 2.0)
                    continue

                if current_phase in (0, 2):
                    yellow_phase = YELLOW_AFTER_GREEN[junction][current_phase]
                    traci.trafficlight.setPhase(junction, yellow_phase)
                    traci.trafficlight.setPhaseDuration(junction, 3.0)
                    transitions[junction] = (
                        target_phase, sim_time + 3.0
                    )
                    print(
                        f"PRIORITY REQUEST: {ambulance_id} at {junction} | "
                        f"{distance:.1f} m | yellow transition started"
                    )

                elif current_phase in (1, 3):
                    transitions[junction] = (
                        target_phase, sim_time + 3.0
                    )
                    print(
                        f"PRIORITY REQUEST: {ambulance_id} at {junction} | "
                        f"already yellow; priority green scheduled"
                    )

                # If already in a natural yellow phase, let it finish.
                # The next simulation steps will re-evaluate the request.

            if sim_time - last_report_time >= 10:
                print(
                    f"TIME {sim_time:.0f}s | "
                    f"Vehicles: {len(vehicles)} | "
                    f"Ambulances present: {len(ambulances)}"
                )

                for ambulance_id in ambulances:
                    print(
                        f"  {ambulance_id}: "
                        f"road={traci.vehicle.getRoadID(ambulance_id)}, "
                        f"speed={traci.vehicle.getSpeed(ambulance_id):.1f} m/s, "
                        f"lane={traci.vehicle.getLaneID(ambulance_id)}"
                    )
                    print(
                        f"  NEXT TLS: {traci.vehicle.getNextTLS(ambulance_id)}"   
                    )
                    print(
                        f"  J3 phase={traci.trafficlight.getPhase('J3')} | "
                        f"J3 state={traci.trafficlight.getRedYellowGreenState('J3')}"
                    )
                    print(
                        f"  WAITING TIME: {traci.vehicle.getWaitingTime(ambulance_id):.1f} s"
                    )
                    print(
                        f"  LINK 1 STATE: "
                        f"{traci.trafficlight.getRedYellowGreenState('J3')[1]}"
                    )

                last_report_time = sim_time

    finally:
        traci.close()


if __name__ == "__main__":
    main()
