
import pandas as pd
from pathlib import Path

FEATURE_FILE = "dataset/features/component_features.csv"
LABEL_FILE = "dataset/labels/component_labels.csv"
OUTPUT_FILE = "dataset/features/training_dataset.csv"

ID_COLS = ["dashboard_id", "candidate_id"]

FEATURE_COLS = [
    "width", "height", "area", "aspect_ratio", "child_count",
    "text_count", "numeric_text_count", "text_density",
    "numeric_density", "vector_count", "line_count",
    "ellipse_count", "rectangle_count", "graphical_count",
    "has_percentage", "has_date_text", "has_chart_word",
    "has_table_word", "has_kpi_word", "has_filter_word",
]

VALID_LABELS = {"KPI_CARD", "CHART", "TABLE", "FILTER", "OTHER", "HEADER", "NAVBAR"}

features = pd.read_csv(FEATURE_FILE, dtype={"dashboard_id": str, "candidate_id": str})
labels = pd.read_csv(LABEL_FILE, dtype=str).fillna("")

# Keep only valid, manually assigned labels
labels["label"] = labels["label"].str.strip()
labels = labels[labels["label"].isin(VALID_LABELS)].copy()

# Avoid accidentally duplicating feature rows during the merge
labels = labels.drop_duplicates(subset=ID_COLS, keep="last")

df = features.merge(
    labels[ID_COLS + ["label"]],
    on=ID_COLS,
    how="inner",
    validate="one_to_one",
)

# Ensure feature values are numeric
for col in FEATURE_COLS:
    df[col] = pd.to_numeric(df[col], errors="coerce")

missing = df[FEATURE_COLS].isna().sum().sum()
if missing:
    print(f"Rows with missing feature values: {missing}")
    df = df.dropna(subset=FEATURE_COLS).copy()

training_df = df[ID_COLS + FEATURE_COLS + ["label"]].copy()

Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
training_df.to_csv(OUTPUT_FILE, index=False)

print("Saved:", OUTPUT_FILE)
print("Training rows:", len(training_df))
print("\nClass distribution:")
print(training_df["label"].value_counts().to_string())
print("\nDashboard15 rows:", (training_df["dashboard_id"] == "dashboard15").sum())
print("Unlabeled rows included: 0")

