
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

FEATURE_FILE = BASE_DIR / "dataset" / "features" / "component_features.csv"
LABEL_FILE = BASE_DIR / "dataset" / "labels" / "component_labels.csv"

# The classes supported by your current XGBoost model.
VALID_LABELS = {"CHART", "FILTER", "KPI_CARD", "OTHER", "TABLE"}


def main():
    if not FEATURE_FILE.exists():
        raise FileNotFoundError(f"Feature file not found: {FEATURE_FILE}")

    if not LABEL_FILE.exists():
        raise FileNotFoundError(f"Label file not found: {LABEL_FILE}")

    features = pd.read_csv(FEATURE_FILE, dtype=str).fillna("")
    labels = pd.read_csv(LABEL_FILE, dtype=str).fillna("")

    required_features = {"dashboard_id", "candidate_id"}
    required_labels = {"dashboard_id", "candidate_id", "label"}

    if not required_features.issubset(features.columns):
        raise ValueError(
            f"Missing feature columns: {required_features - set(features.columns)}"
        )

    if not required_labels.issubset(labels.columns):
        raise ValueError(
            f"Missing label columns: {required_labels - set(labels.columns)}"
        )

    # Normalize IDs and labels for comparison.
    features["dashboard_id"] = features["dashboard_id"].str.strip()
    features["candidate_id"] = features["candidate_id"].str.strip()

    labels["dashboard_id"] = labels["dashboard_id"].str.strip()
    labels["candidate_id"] = labels["candidate_id"].str.strip()
    labels["label"] = labels["label"].str.strip().str.upper()

    # Report dashboard IDs available in the files.
    print("\nDASHBOARDS AVAILABLE")
    print("--------------------")
    print(
        features.groupby("dashboard_id").size().sort_index().to_string()
    )

    # Count only valid, non-empty labels as labeled.
    valid_existing = labels["label"].isin(VALID_LABELS)

    print("\nEXISTING VALID LABEL COUNTS")
    print("---------------------------")
    print(labels.loc[valid_existing, "label"].value_counts().to_string())

    # Identify candidates with no valid label.
    labeled_pairs = set(
        zip(
            labels.loc[valid_existing, "dashboard_id"],
            labels.loc[valid_existing, "candidate_id"],
        )
    )

    features["is_labeled"] = [
        (dashboard_id, candidate_id) in labeled_pairs
        for dashboard_id, candidate_id in zip(
            features["dashboard_id"], features["candidate_id"]
        )
    ]

    unlabeled = features.loc[~features["is_labeled"]].copy()

    output_file = (
        BASE_DIR / "dataset" / "labels" / "unlabeled_candidates.csv"
    )
    unlabeled.to_csv(output_file, index=False)

    print("\nRESULT")
    print("------")
    print("Total candidates:", len(features))
    print("Candidates with valid labels:", int(features["is_labeled"].sum()))
    print("Candidates needing labels:", len(unlabeled))
    print("Unlabeled candidates saved to:", output_file)

    if not unlabeled.empty:
        print("\nUnlabeled candidates per dashboard:")
        print(
            unlabeled.groupby("dashboard_id")
            .size()
            .sort_index()
            .to_string()
        )

    print(
        "\nNOTE: This script identifies unlabeled candidates. "
        "It does not invent or assign labels."
    )


if __name__ == "__main__":
    main()
