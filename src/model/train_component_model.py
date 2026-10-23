"""
Train an XGBoost component classifier from component_features_labeled.csv.

Run from C:\figma_proj:
    python train_component_model.py

Outputs:
    models/component_classifier.json
    models/component_classifier.joblib
    outputs/labeled_test_predictions.csv
    outputs/unlabeled_candidate_predictions.csv
    outputs/classification_report.txt
"""

from pathlib import Path
import sys

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from xgboost import XGBClassifier
import joblib

ROOT = Path(__file__).resolve().parent

# Find the CSV even if its filename has an unexpected suffix
matches = list(ROOT.glob("component_features_labeled*"))

if not matches:
    raise FileNotFoundError(
        f"No labeled CSV found in {ROOT}"
    )

CSV_PATH = matches[0]
MODEL_DIR = ROOT / "models"
OUTPUT_DIR = ROOT / "outputs"

print("CSV found:", CSV_PATH)

FEATURES = [
    "width", "height", "area", "aspect_ratio", "child_count", "text_count",
    "numeric_text_count", "text_density", "numeric_density", "vector_count",
    "line_count", "ellipse_count", "rectangle_count", "graphical_count",
    "has_percentage", "has_date_text", "has_chart_word", "has_table_word",
    "has_kpi_word", "has_filter_word",
]


def main():
    if not CSV_PATH.exists():
        sys.exit(
            f"CSV not found: {CSV_PATH}\n"
            "Put component_features_labeled.csv in the same folder as this script."
        )

    df = pd.read_csv(CSV_PATH)
    required = FEATURES + ["label"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        sys.exit(f"CSV is missing required columns: {missing}")

    # Keep rows with a real label. Empty strings and whitespace count as unlabeled.
    labels = df["label"].astype("string").str.strip()
    labeled_mask = labels.notna() & labels.ne("")
    train_df = df.loc[labeled_mask].copy()
    train_df["label"] = labels.loc[labeled_mask].astype(str)

    if train_df["label"].nunique() < 2:
        sys.exit("Need at least two different non-empty labels to train.")

    # Convert feature columns to numeric and replace missing/infinite values safely.
    X = train_df[FEATURES].apply(pd.to_numeric, errors="coerce")
    X = X.replace([float("inf"), float("-inf")], pd.NA)
    medians = X.median().fillna(0)
    X = X.fillna(medians)

    encoder = LabelEncoder()
    y = encoder.fit_transform(train_df["label"])

    # Stratify where possible so each class is represented in the holdout set.
    class_counts = train_df["label"].value_counts()
    stratify = y if class_counts.min() >= 2 else None
    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, train_df.index, test_size=0.20, random_state=42, stratify=stratify
    )

    model = XGBClassifier(
        objective="multi:softprob",
        num_class=len(encoder.classes_),
        n_estimators=350,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_weight=2,
        reg_lambda=1.0,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test).astype(int)
    report = classification_report(
        y_test, pred, labels=list(range(len(encoder.classes_))),
        target_names=encoder.classes_, zero_division=0
    )
    accuracy = accuracy_score(y_test, pred)
    cm = confusion_matrix(y_test, pred, labels=list(range(len(encoder.classes_))))

    MODEL_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    model.save_model(str(MODEL_DIR / "component_classifier.json"))
    joblib.dump(
        {"model": model, "label_encoder": encoder, "features": FEATURES,
         "medians": medians.to_dict()},
        MODEL_DIR / "component_classifier.joblib"
    )

    test_out = train_df.loc[idx_test, [
        c for c in ["dashboard_id", "candidate_id", "name", "label"] if c in train_df.columns
    ]].copy()
    test_out["predicted_label"] = encoder.inverse_transform(pred)
    test_out["correct"] = test_out["label"].astype(str) == test_out["predicted_label"]
    test_out.to_csv(OUTPUT_DIR / "labeled_test_predictions.csv", index=False)

    unlabeled_df = df.loc[~labeled_mask].copy()
    if not unlabeled_df.empty:
        Xu = unlabeled_df[FEATURES].apply(pd.to_numeric, errors="coerce")
        Xu = Xu.replace([float("inf"), float("-inf")], pd.NA).fillna(medians)
        probs = model.predict_proba(Xu)
        pred_ids = probs.argmax(axis=1)
        unlabeled_df["predicted_label"] = encoder.inverse_transform(pred_ids)
        unlabeled_df["confidence"] = probs.max(axis=1).round(4)
        unlabeled_df["needs_review"] = unlabeled_df["confidence"] < 0.70
        unlabeled_df.to_csv(OUTPUT_DIR / "unlabeled_candidate_predictions.csv", index=False)

    with open(OUTPUT_DIR / "classification_report.txt", "w", encoding="utf-8") as f:
        f.write(f"Rows in CSV: {len(df)}\n")
        f.write(f"Labelled rows used: {len(train_df)}\n")
        f.write(f"Unlabelled rows predicted: {len(unlabeled_df)}\n")
        f.write(f"Classes: {', '.join(encoder.classes_)}\n")
        f.write(f"Holdout accuracy: {accuracy:.4f}\n\n")
        f.write("Classification report:\n")
        f.write(report)
        f.write("\nConfusion matrix (rows=true, columns=predicted; class order below):\n")
        f.write(", ".join(encoder.classes_) + "\n")
        f.write(str(cm) + "\n")

    print("\nTRAINING COMPLETE")
    print(f"Rows in CSV: {len(df)}")
    print(f"Labelled rows used: {len(train_df)}")
    print(f"Unlabelled candidates predicted: {len(unlabeled_df)}")
    print(f"Classes: {', '.join(encoder.classes_)}")
    print(f"Holdout accuracy: {accuracy:.3f}")
    print("\nClassification report:\n")
    print(report)
    print("\nCreated:")
    print(f"  {MODEL_DIR / 'component_classifier.json'}")
    print(f"  {MODEL_DIR / 'component_classifier.joblib'}")
    print(f"  {OUTPUT_DIR / 'labeled_test_predictions.csv'}")
    print(f"  {OUTPUT_DIR / 'unlabeled_candidate_predictions.csv'}")
    print(f"  {OUTPUT_DIR / 'classification_report.txt'}")
    print("\nReview FILTER results carefully: that class has very few labelled examples.")


if __name__ == "__main__":
    main()
