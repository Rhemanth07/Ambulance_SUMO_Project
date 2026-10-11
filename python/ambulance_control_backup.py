


import os
import traci

SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"
SUMO_GUI = os.path.join(SUMO_HOME, "bin", "sumo-gui.exe")
CONFIG = r"C:\Ambulance_SUMO_Project\simulation\ambulance.sumocfg"

AMBULANCE_ID = "ambulance1"
JUNCTIONS = ["J1", "J2", "J3"]
DETECTION_RANGE = 300.0
TRAFFIC_RADIUS = 50.0

def distance(a, b):
    return ((a[0] - b[0])**2 + (a[1] - b[1])**2)**0.5

traci.start([SUMO_GUI, "-c", CONFIG, "--start", "--delay", "500"])

print("TRAFFIC SENSING AND AMBULANCE DETECTION STARTED")

try:
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        vehicles = traci.vehicle.getIDList()

        # Simulated traffic sensing near each junction
        for junction in JUNCTIONS:
            jpos = traci.junction.getPosition(junction)
            count = 0

            for vid in vehicles:
                if vid == AMBULANCE_ID:
                    continue
                pos = traci.vehicle.getPosition(vid)
                if distance(pos, jpos) <= TRAFFIC_RADIUS:
                    count += 1

            if count >= 5:
                level = "HIGH"
            elif count >= 2:
                level = "MEDIUM"
            else:
                level = "LOW"

            print(f"TRAFFIC {junction}: {level} ({count} vehicles within 50 m)")

        # Ambulance detection within 300 m
        
        # Ambulance detection and signal priority
        if AMBULANCE_ID in vehicles:
            apos = traci.vehicle.getPosition(AMBULANCE_ID)

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

                # Give the ambulance straight-through priority
                # at J1 or J2; stop the conflicting movements.
                if nearest in ("J1", "J2"):
                    traci.trafficlight.setRedYellowGreenState(
                        nearest, "rGr"
                    )
                    print(
                        f"SIGNAL PRIORITY: {nearest} "
                        f"straight-through movement requested GREEN"
                    )


finally:
    traci.close()
