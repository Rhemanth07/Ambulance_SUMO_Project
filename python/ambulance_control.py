
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
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


traci.start([SUMO_GUI, "-c", CONFIG, "--start", "--delay", "500"])

original_states = {}
priority_junction = None
start_time = None
arrival_time = None
ambulance_seen = False

try:
    for junction in JUNCTIONS:
        original_states[junction] = (
            traci.trafficlight.getRedYellowGreenState(junction)
        )

    print("AMBULANCE GREEN-CORRIDOR TEST STARTED")

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        vehicles = traci.vehicle.getIDList()
        sim_time = traci.simulation.getTime()

        if AMBULANCE_ID in vehicles and start_time is None:
            start_time = sim_time
            ambulance_seen = True
            print(f"AMBULANCE DEPARTED at {start_time:.1f} seconds")

        for junction in JUNCTIONS:
            jpos = traci.junction.getPosition(junction)
            count = sum(
                1
                for vid in vehicles
                if vid != AMBULANCE_ID
                and distance(
                    traci.vehicle.getPosition(vid), jpos
                ) <= TRAFFIC_RADIUS
            )

            level = "HIGH" if count >= 5 else (
                "MEDIUM" if count >= 2 else "LOW"
            )
            print(f"TRAFFIC {junction}: {level} ({count} vehicles)")

        # Detect actual arrival using SUMO's arrived-vehicle list
        if AMBULANCE_ID in traci.simulation.getArrivedIDList():
            arrival_time = sim_time
            print("\n===== SCENARIO 1 RESULTS =====")
            print(f"Departure time: {start_time:.1f} seconds")
            print(f"Arrival time: {arrival_time:.1f} seconds")
            print(f"Travel time: {arrival_time - start_time:.1f} seconds")
            break

        if AMBULANCE_ID not in vehicles:
            continue

        ambulance_pos = traci.vehicle.getPosition(AMBULANCE_ID)
        distances = {
            j: distance(
                ambulance_pos, traci.junction.getPosition(j)
            )
            for j in JUNCTIONS
        }

        nearest = min(distances, key=distances.get)
        d = distances[nearest]

        if d <= DETECTION_RANGE and priority_junction != nearest:
            if priority_junction is not None:
                old_state = original_states[priority_junction]
                traci.trafficlight.setRedYellowGreenState(
                    priority_junction, old_state
                )

            state = traci.trafficlight.getRedYellowGreenState(nearest)
            new_state = ["r"] * len(state)
            links = traci.trafficlight.getControlledLinks(nearest)

            for i, link_group in enumerate(links):
                if i >= len(new_state):
                    break
                for link in link_group:
                    if link[1] in ("E1_0", "E2_0", "E9_0"):
                        new_state[i] = "G"
                        break

            traci.trafficlight.setRedYellowGreenState(
                nearest, "".join(new_state)
            )
            priority_junction = nearest

            print(
                f"AMBULANCE DETECTED: {nearest}, "
                f"distance={d:.1f} m"
            )
            print(f"GREEN PRIORITY REQUESTED: {nearest}")

    if arrival_time is None:
        print("\nScenario 1 ended without a recorded ambulance arrival.")
        if not ambulance_seen:
            print(
                f"Check whether vehicle ID '{AMBULANCE_ID}' "
                "exists in the route file."
            )

finally:
    for junction, state in original_states.items():
        try:
            traci.trafficlight.setRedYellowGreenState(
                junction, state
            )
        except traci.TraCIException:
            pass

    if traci.isLoaded():
        traci.close()
