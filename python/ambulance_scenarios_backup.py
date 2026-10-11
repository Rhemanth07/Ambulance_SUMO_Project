
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
