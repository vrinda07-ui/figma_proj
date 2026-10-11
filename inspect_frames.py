import json
from pathlib import Path
from collections import Counter

data = json.loads(Path("dataset/new_dashboard/figma_data.json").read_text(encoding="utf-8"))

def inspect(node):
    if not isinstance(node, dict):
        return

    if node.get("name", "").lower() in {"b esquerda", "b direito", "b meio"}:
        counts = Counter()
        examples = []

        def collect(n, depth=0):
            if not isinstance(n, dict):
                return
            counts[n.get("type", "UNKNOWN")] += 1
            if len(examples) < 30:
                examples.append("  " * depth + f'{n.get("type")}: {n.get("name", "")}')
            for child in n.get("children", []):
                collect(child, depth + 1)

        collect(node)
        print(f"\n=== {node['name']} ===")
        print("Node types:", dict(counts))
        print("\n".join(examples))

    for child in node.get("children", []):
        inspect(child)

inspect(data)
