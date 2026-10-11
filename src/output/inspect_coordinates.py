
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = ROOT / "dataset" / "new_dashboard" / "figma_data.json"

TARGET_IDS = [
    "1:242",
    "I1:242;11:908",
    "I1:242;11:905",
    "I1:242;11:906",
    "I1:242;11:703",
    "I1:242;11:736",
    "I1:242;11:732",
    "I1:242;11:733",
]

with open(INPUT_FILE, encoding="utf-8") as f:
    data = json.load(f)

nodes = {}
parents = {}

def walk(node, parent=None):
    if not isinstance(node, dict):
        return

    node_id = node.get("id")
    if node_id is not None:
        node_id = str(node_id)
        nodes[node_id] = node
        parents[node_id] = parent

    for child in node.get("children", []):
        walk(child, node_id)

walk(data.get("document", {}))

print("Total nested nodes:", len(nodes))

for node_id in TARGET_IDS:
    node = nodes.get(node_id)

    print("\n" + "=" * 60)
    print("ID:", node_id)

    if node is None:
        print("Node not found in document tree")
        continue

    print("Name:", node.get("name"))
    print("Type:", node.get("type"))
    print("Parent ID:", parents.get(node_id))

    bbox = node.get("absoluteBoundingBox")
    print("Absolute bounding box:", bbox)

    if bbox:
        print(
            "x =", bbox.get("x"),
            "| y =", bbox.get("y"),
            "| width =", bbox.get("width"),
            "| height =", bbox.get("height")
        )

# Inspect the dashboard frame.
dashboard = nodes.get("1:242")
if dashboard:
    print("\n" + "=" * 60)
    print("DASHBOARD FRAME")
    print("Name:", dashboard.get("name"))
    print("Type:", dashboard.get("type"))
    print("Absolute bounding box:", dashboard.get("absoluteBoundingBox"))
    print("Direct children:")

    for child in dashboard.get("children", []):
        print(
            child.get("id"),
            "|", child.get("name"),
            "|", child.get("type"),
            "|", child.get("absoluteBoundingBox")
        )
