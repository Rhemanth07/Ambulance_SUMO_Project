
import os
import traci
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG = str(ROOT / "simulation" / "ambulance.sumocfg")
ROUTES = str(ROOT / "routes" / "ambulance.rou.xml")
TEMP_ROUTES = str(ROOT / "routes" / "scenario3_temp.rou.xml")

SIMULATION_END = 600


def main():
    tree = ET.parse(ROUTES)
    root = tree.getroot()

    # Remove existing vehicles and flows for an isolated test
    for element in list(root):
        if element.tag in ("vehicle", "flow"):
            root.remove(element)

    # Add two ambulances travelling in opposite directions
    ET.SubElement(root, "vehicle", {
        "id": "ambulance_forward_test",
        "type": "ambulance",
        "route": "mainRoute",
        "depart": "10"
    })

    ET.SubElement(root, "vehicle", {
        "id": "ambulance_reverse_test",
        "type": "ambulance",
        "route": "reverseRoute",
        "depart": "70"
    })

    tree.write(TEMP_ROUTES, encoding="UTF-8", xml_declaration=True)

    sumo_cmd = [
        "sumo-gui",
        "-c", CONFIG,
        "--route-files", TEMP_ROUTES,
        "--start",
        "--delay", "300",
        "--end", str(SIMULATION_END)
    ]

    junction_phases = {
        "J1": {"forward": 0, "reverse": 0},
        "J2": {"forward": 2, "reverse": 2},
        "J3": {"forward": 0, "reverse": 0},    }

    ambulance_routes = {
        "ambulance_forward_test": "forward",
        "ambulance_reverse_test": "reverse",
    }

    try:
        traci.start(sumo_cmd)

        print("SCENARIO 3: TWO AMBULANCES")
        print("Forward ambulance departs at 10 seconds")
        print("Reverse ambulance departs at 70 seconds")

        
        active_preemptions = set()

        while traci.simulation.getMinExpectedNumber() > 0:
            requested_phases = {}

            # Find approaching ambulances
            for vehicle_id in traci.vehicle.getIDList():
                if vehicle_id not in ambulance_routes:
                    continue

                direction = ambulance_routes[vehicle_id]
                next_tls = traci.vehicle.getNextTLS(vehicle_id)

                if not next_tls:
                    continue

                tls_id, link_index, distance, signal_state = next_tls[0]

                if tls_id not in junction_phases:
                    continue

                if distance < 100:
                    requested_phases[tls_id] = (
                        junction_phases[tls_id][direction]
                    )

            # Activate preemption only when needed
            for tls_id, desired_phase in requested_phases.items():
                current_phase = traci.trafficlight.getPhase(tls_id)

                if current_phase != desired_phase:
                    traci.trafficlight.setPhase(
                        tls_id, desired_phase
                    )

                active_preemptions.add(tls_id)

            # Hand control back to the normal signal cycle
            for tls_id in list(active_preemptions):
                if tls_id not in requested_phases:
                    traci.trafficlight.setPhaseDuration(tls_id, 0)
                    active_preemptions.remove(tls_id)

            traci.simulationStep()

            sim_time = traci.simulation.getTime()

            if int(sim_time) % 10 == 1:
                print(f"TIME {sim_time:.0f}s")

                for vehicle_id in traci.vehicle.getIDList():
                    print(
                        f"  {vehicle_id}: "
                        f"road={traci.vehicle.getRoadID(vehicle_id)}, "
                        f"speed={traci.vehicle.getSpeed(vehicle_id):.1f} m/s"
                    )


    finally:
        if traci.isLoaded():
            traci.close()


if __name__ == "__main__":
    main()
