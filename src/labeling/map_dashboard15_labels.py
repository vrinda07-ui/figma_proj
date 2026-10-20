
import ast
import json
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[2]

LABELS_FILE = BASE / "src" / "labeling" / "dashboard15_labels.py"
CANDIDATES_FILE = BASE / "dataset" / "candidates" / "dashboard15_candidates.json"
OUTPUT_FILE = BASE / "dataset" / "labels" / "component_labels.csv"

# Load the LABELS dictionary without executing the Python file.
source = LABELS_FILE.read_text(encoding="utf-8")
tree = ast.parse(source)

labels = None
for node in tree.body:
    if isinstance(node, ast.Assign):
        if any(isinstance(target, ast.Name) and target.id == "LABELS"
               for target in node.targets):
            labels = ast.literal_eval(node.value)
            break

if labels is None:
    raise ValueError("Could not find LABELS = {...} in dashboard15_labels.py")

# Map Claude's detailed labels to the five XGBoost classes.
CLASS_MAP = {
    "screen": "OTHER",
    "top_header": "OTHER",
    "primary_nav": "OTHER",
    "page_header": "OTHER",
    "filter_panel": "FILTER",
    "kpi_group": "OTHER",
    "kpi_card": "KPI_CARD",
    "section": "OTHER",
    "chart": "CHART",
    "chart_inner": "OTHER",
    "legend": "OTHER",
    "table": "TABLE",
    "table_heading": "OTHER",
    "table_column": "OTHER",
    "table_row": "TABLE",
    "badge": "OTHER",
    "callout": "OTHER",
    "other": "OTHER",
}

data = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
candidates = data["candidates"]

# Convert node IDs in LABELS to the model's five classes.
rows = []
unmatched = []

for category, node_ids in labels.items():
    if category not in CLASS_MAP:
        print(f"Warning: unmapped category: {category}")
        continue

    if isinstance(node_ids, str):
        node_ids = [node_ids]

    for node_id in node_ids:
        # Handles accidental combined IDs by checking each part.
        parts = [part.strip() for part in str(node_id).split(";")]
        for part in parts:
            clean_id = part.removeprefix("I").strip()
            matched = [
                candidate for candidate in candidates
                if str(candidate.get("candidate_id")) == clean_id
            ]

            if not matched:
                unmatched.append((category, clean_id))
                continue

            for candidate in matched:
                rows.append({
                    "dashboard_id": "dashboard15",
                    "candidate_id": clean_id,
                    "name": candidate.get("name", ""),
                    "label": CLASS_MAP[category],
                })

new_df = pd.DataFrame(rows, columns=[
    "dashboard_id", "candidate_id", "name", "label"
])

if new_df.empty:
    raise ValueError(
        "No labels matched candidate IDs. Check the LABELS dictionary IDs."
    )

# Remove duplicate IDs in the new labels.
new_df = new_df.drop_duplicates(
    subset=["dashboard_id", "candidate_id"], keep="last"
)

# Preserve all existing labels for other dashboards and IDs.
if OUTPUT_FILE.exists():
    existing = pd.read_csv(OUTPUT_FILE).fillna("")
else:
    existing = pd.DataFrame(columns=[
        "dashboard_id", "candidate_id", "name", "label"
    ])

# Replace only dashboard15 rows for IDs labeled by this script.
replace_ids = set(new_df["candidate_id"])
keep = ~(
    (existing["dashboard_id"].astype(str) == "dashboard15")
    & (existing["candidate_id"].astype(str).isin(replace_ids))
)

combined = pd.concat([existing.loc[keep], new_df], ignore_index=True)
combined = combined.drop_duplicates(
    subset=["dashboard_id", "candidate_id"], keep="last"
)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
combined.to_csv(OUTPUT_FILE, index=False)

print(f"Claude label entries: {sum(len(v) if isinstance(v, list) else 1 for v in labels.values())}")
print(f"Matched labeled candidates: {len(new_df)}")
print(f"Unmatched node IDs: {len(unmatched)}")
print(f"Updated labels file: {OUTPUT_FILE}")

if unmatched:
    print("\nFirst 20 unmatched IDs:")
    for category, node_id in unmatched[:20]:
        print(f"  {category}: {node_id}")

print("\nDashboard15 label counts:")
print(new_df["label"].value_counts().to_string())
