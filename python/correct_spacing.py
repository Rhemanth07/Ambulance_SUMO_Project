

import os
import traci

SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"
SUMO_GUI = os.path.join(SUMO_HOME, "bin", "sumo-gui.exe")
CONFIG = r"C:\Ambulance_SUMO_Project\simulation\ambulance.sumocfg"

DETECTION_RANGE = 300.0
TRAFFIC_RADIUS = 50.0
AMBULANCE_ID = "ambulance1"
JUNCTIONS = ["J1", "J2", "J3"]

def distance(a, b):
    return ((a[0] - b[0])**2 + (a[1] - b[1])**2)**0.5

traci.start([
    SUMO_GUI, "-c", CONFIG, "--start", "--delay", "500"
])

try:
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        vehicle_ids = traci.vehicle.getIDList()
        positions = {
            vid: traci.vehicle.getPosition(vid)
            for vid in vehicle_ids
        }

        # Estimate local traffic density near every junction.
        for junction in JUNCTIONS:
            jpos = traci.junction.getPosition(junction)

            nearby = [
                vid for vid, pos in positions.items()
                if vid != AMBULANCE_ID
                and distance(pos, jpos) <= TRAFFIC_RADIUS
            ]

            if len(nearby) >= 5:
                traffic_level = "HIGH"
            elif len(nearby) >= 2:
                traffic_level = "MEDIUM"
            else:
                traffic_level = "LOW"

            print(
                f"{junction}: traffic={traffic_level}, "
                f"vehicles within {TRAFFIC_RADIUS:.0f} m={len(nearby)}"
            )

        # Detect ambulance within 300 m of the nearest junction.
        if AMBULANCE_ID in positions:
            apos = positions[AMBULANCE_ID]

            distances = {
                j: distance(apos, traci.junction.getPosition(j))
                for j in JUNCTIONS
            }

            nearest = min(distances, key=distances.get)
            d = distances[nearest]

            if d <= DETECTION_RANGE:
                print(
                    f"AMBULANCE DETECTED: {nearest}, "
                    f"distance={d:.1f} m"
                )

finally:
    traci.close()

