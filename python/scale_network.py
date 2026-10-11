
import xml.etree.ElementTree as ET
from pathlib import Path

network = Path(r"C:\Ambulance_SUMO_Project\network\ambulance.net.xml")
backup = Path(r"C:\Ambulance_SUMO_Project\network\ambulance_backup.net.xml")

tree = ET.parse(network)
root = tree.getroot()

# Current junction positions
positions = {}
for junction in root.findall("junction"):
    if junction.get("id") in ("J1", "J2", "J3"):
        positions[junction.get("id")] = (
            float(junction.get("x")),
            float(junction.get("y"))
        )

if not all(j in positions for j in ("J1", "J2", "J3")):
    raise ValueError(f"Missing junction IDs. Found: {positions}")

# Scale coordinates so J1-J2 is 300 coordinate metres.
x1 = positions["J1"][0]
x2 = positions["J2"][0]
factor = 300.0 / (x2 - x1)

def scale_pair(pair):
    x, y = map(float, pair.split(","))
    return f"{x1 + (x - x1) * factor:.3f},{y * factor:.3f}"

for element in root.iter():
    for attr in ("x", "y"):
        if element.tag == "junction" and element.get("id") in positions:
            pass
    if element.tag == "junction" and element.get("x") is not None:
        x, y = float(element.get("x")), float(element.get("y"))
        element.set("x", f"{x1 + (x - x1) * factor:.3f}")
        element.set("y", f"{y * factor:.3f}")

    for attr in ("shape",):
        value = element.get(attr)
        if value:
            element.set(
                attr,
                " ".join(scale_pair(p) for p in value.split())
            )

tree.write(network, encoding="UTF-8", xml_declaration=True)
print(f"Scaled network coordinates by {factor:.3f}.")
print("Junction IDs and edge IDs were preserved.")
print("J1-J2 target spacing: 300 coordinate metres.")
print("J2-J3 spacing will be checked next.")
