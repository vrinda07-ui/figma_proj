
import pandas as pd
from pathlib import Path

FEATURE_FILE = "dataset/features/component_features.csv"
LABEL_FILE = "dataset/labels/component_labels.csv"
OUTPUT_FILE = "dataset/labels/unlabeled_candidates.csv"

features = pd.read_csv(FEATURE_FILE, dtype=str)
labels = pd.read_csv(LABEL_FILE, dtype=str)

# Only candidates with a non-empty label count as labeled.
labeled = labels[
    labels["label"].notna()
    & labels["label"].str.strip().ne("")
][["dashboard_id", "candidate_id"]].drop_duplicates()

unlabeled = features.merge(
    labeled,
    on=["dashboard_id", "candidate_id"],
    how="left",
    indicator=True
)

unlabeled = unlabeled[
    unlabeled["_merge"] == "left_only"
].drop(columns=["_merge"])

columns = [
    "dashboard_id", "candidate_id", "name",
    "width", "height", "child_count", "text_count",
    "numeric_text_count", "has_percentage", "has_date_text",
    "has_chart_word", "has_table_word", "has_kpi_word"
]

unlabeled = unlabeled[columns]
Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
unlabeled.to_csv(OUTPUT_FILE, index=False)

print("Actually unlabeled candidates:", len(unlabeled))
print("\nCandidates per dashboard:")
print(unlabeled.groupby("dashboard_id").size().to_string())
print("\nSaved to:", OUTPUT_FILE)
