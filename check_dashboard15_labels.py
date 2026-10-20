
import ast
import json
from pathlib import Path

labels_path = Path("src/labeling/dashboard15_labels.py")
candidates_path = Path("dataset/candidates/dashboard15_candidates.json")

tree = ast.parse(labels_path.read_text(encoding="utf-8"))
labels = None

for node in tree.body:
    if isinstance(node, ast.Assign):
        if any(
            isinstance(t, ast.Name) and t.id == "LABELS"
            for t in node.targets
        ):
            labels = ast.literal_eval(node.value)
            break

data = json.loads(candidates_path.read_text(encoding="utf-8"))
candidate_ids = {str(c["candidate_id"]) for c in data["candidates"]}

print("Candidate ID examples:", list(candidate_ids)[:10])
print("LABELS type:", type(labels).__name__)

for category, ids in labels.items():
    if isinstance(ids, dict):
        ids = list(ids.keys())
    elif isinstance(ids, str):
        ids = [ids]

    ids = list(ids)
    matches = [
        str(x).strip().removeprefix("I")
        for x in ids
        if str(x).strip().removeprefix("I") in candidate_ids
    ]

    print(f"{category}: {len(matches)} matches")
    print("  Examples:", ids[:3])
