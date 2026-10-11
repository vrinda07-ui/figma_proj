import pandas as pd

FEATURE_FILE = "dataset/features/component_features.csv"
LABEL_FILE = "dataset/labels/component_labels.csv"
OUTPUT_FILE = "dataset/labels/unlabeled_candidates.csv"

features = pd.read_csv(FEATURE_FILE)
labels = pd.read_csv(LABEL_FILE)

# Keep only the IDs of already labeled candidates
labeled_ids = labels[["dashboard_id", "candidate_id"]].drop_duplicates()

# Find candidates that don't have a label yet
unlabeled = features.merge(
    labeled_ids,
    on=["dashboard_id", "candidate_id"],
    how="left",
    indicator=True
)

unlabeled = unlabeled[
    unlabeled["_merge"] == "left_only"
].drop(columns=["_merge"])

# Keep useful information for manual labeling
columns = [
    "dashboard_id",
    "candidate_id",
    "name",
    "width",
    "height",
    "child_count",
    "text_count",
    "numeric_text_count",
    "has_percentage",
    "has_date_text",
    "has_chart_word",
    "has_table_word",
    "has_kpi_word",
]

unlabeled = unlabeled[columns]

unlabeled.to_csv(OUTPUT_FILE, index=False)

print("=" * 60)
print("UNLABELED CANDIDATES")
print("=" * 60)

print("Total unlabeled:", len(unlabeled))
print("\nCandidates:")
print(unlabeled.to_string(index=False))

print("\nSaved to:")
print(OUTPUT_FILE)