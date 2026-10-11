# SUMO-Integrated Edge-IoT Based Adaptive Multi-Junction Traffic Signal Preemption for Emergency Ambulance

## Project Overview
This project simulates emergency ambulance traffic signal preemption using Eclipse SUMO, Python, and TraCI. It evaluates ambulance movement across multiple junctions under normal and heavy traffic conditions.

## Project Structure
- `network/` — Road network and traffic signals
- `routes/` — Vehicle types, routes, and traffic flows
- `simulation/` — SUMO configuration
- `python/` — Python controller and scenario scripts
- `results/` — Simulation results
- `screenshots/` — Simulation screenshots

## Requirements
- Windows 10/11
- Eclipse SUMO 1.27.1
- Python 3.12 or compatible version
- SUMO TraCI Python interface

## Setup
1. Install Eclipse SUMO and Python.
2. Download or clone this repository.
3. Configure `SUMO_HOME` to point to your SUMO installation directory.
4. Ensure the SUMO `bin` directory is available in your PATH.
5. Ensure Python can import TraCI from the SUMO `tools` directory.

## Run the Scenarios

Open Command Prompt in the project root folder.

### Scenario 1 — Single Ambulance
```bat
python python\ambulance_control.py
```

### Scenario 2 — Scenario Tests
```bat
python python\ambulance_scenarios.py
```

### Scenario 3 — Two Ambulances
```bat
python python\scenario3_two_ambulances.py
```

### Scenario 4 — Heavy Traffic
```bat
python python\scenario4_heavy_traffic.py
```

## Run SUMO GUI Directly
```bat
sumo-gui -c simulation\ambulance.sumocfg
```

Running the GUI directly loads the network and routes; it does not necessarily run the Python ambulance controller.

## Troubleshooting
- **SUMO not found:** Check the SUMO installation and PATH.
- **TraCI import error:** Check `SUMO_HOME` and the SUMO `tools` directory.
- **Configuration or route file not found:** Run commands from the project root and verify the folder structure.
- **Invalid XML:** Check XML syntax and closing tags.
- **Missing traffic:** Check that route flows are enabled and start the simulation from time zero.

## Results
Add measured travel times, arrival times, signal-response observations, and screenshots for each scenario.

## Limitations
This is a simulation prototype. Signal-control logic must be validated for conflicting traffic movements and safe signal transitions before any real-world deployment.
