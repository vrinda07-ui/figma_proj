
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
INPUT = BASE / "dataset" / "dashboards" / "dashboard15.json"
OUTPUT = BASE / "dataset" / "labels" / "dashboard15_nodes_for_claude.json"

with INPUT.open(encoding="utf-8") as f:
    data = json.load(f)

nodes = []

def walk(node, parent_name=""):
    name = node.get("name", "")
    node_type = node.get("type", "")

    # Collect text belonging to this node and its descendants.
    texts = []

    def collect_text(n):
        if n.get("type") == "TEXT":
            content = n.get("characters", "")
            if content:
                texts.append(content)
        for child in n.get("children", []):
            collect_text(child)

    collect_text(node)

    # Keep meaningful structural nodes, not every tiny vector.
    if node_type in {
        "FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE",
        "GROUP", "TEXT"
    }:
        box = node.get("absoluteBoundingBox") or node.get("size") or {}

        nodes.append({
            "id": node.get("id"),
            "name": name,
            "type": node_type,
            "parent": parent_name,
            "width": box.get("width"),
            "height": box.get("height"),
            "text": " | ".join(texts[:20])[:1000],
            "child_count": len(node.get("children", []))
        })

    for child in node.get("children", []):
        walk(child, name or parent_name)

walk(data.get("document", data))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(nodes, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("Nodes extracted:", len(nodes))
print("Output file:", OUTPUT)
print("File size (KB):", round(OUTPUT.stat().st_size / 1024, 1))
