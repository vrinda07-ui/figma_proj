
import json
import pickle
from pathlib import Path

import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from xgboost import XGBClassifier


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA_PATH = ROOT / "dataset" / "features" / "labeled_data.csv"
MODEL_DIR = ROOT / "models" / "xgboost_labeled"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CSV STRUCTURE
# The CSV has NO header row.
# ============================================================

COLUMNS = [
    "dashboard_id",
    "candidate_id",
    "component_name",
    "width",
    "height",
    "area",
    "aspect_ratio",
    "child_count",
    "text_count",
    "numeric_text_count",
    "text_density",
    "numeric_density",
    "vector_count",
    "line_count",
    "ellipse_count",
    "rectangle_count",
    "graphical_count",
    "has_percentage",
    "has_date_text",
    "has_chart_word",
    "has_table_word",
    "has_kpi_word",
    "has_filter_word",
    "label",
]

# These must match the features used by your extractor.
FEATURE_COLUMNS = [
    "width",
    "height",
    "area",
    "aspect_ratio",
    "child_count",
    "text_count",
    "numeric_text_count",
    "text_density",
    "numeric_density",
    "vector_count",
    "line_count",
    "ellipse_count",
    "rectangle_count",
    "graphical_count",
    "has_percentage",
    "has_date_text",
    "has_chart_word",
    "has_table_word",
    "has_kpi_word",
    "has_filter_word",
]


# ============================================================
# LOAD DATA
# ============================================================

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Labeled CSV not found:\n{DATA_PATH}\n\n"
            "Place labeled_data.csv in dataset/features/."
        )

    df = pd.read_csv(
        DATA_PATH,
        header=None,
        names=COLUMNS,
        encoding="utf-8-sig",
    )

    # Remove completely empty rows and normalize labels.
    df = df.dropna(subset=["label"]).copy()
    df["label"] = df["label"].astype(str).str.strip().str.upper()

    # Convert model features to numeric values.
    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remove rows without usable labels.
    df = df[df["label"] != ""].copy()

    # Fill missing numeric values using training-data medians.
    medians = df[FEATURE_COLUMNS].median().fillna(0)
    X = df[FEATURE_COLUMNS].fillna(medians)
    y_text = df["label"]

    if len(df) == 0:
        raise ValueError("No labeled rows were found in the CSV.")

    print("\n========== DATASET ==========")
    print(f"CSV: {DATA_PATH}")
    print(f"Total labeled rows: {len(df)}")
    print(f"Unique dashboards: {df['dashboard_id'].nunique()}")
    print("\nLabel counts:")
    print(df["label"].value_counts().to_string())

    # Encode class names as numbers for XGBoost.
    encoder = LabelEncoder()
    y = encoder.fit_transform(y_text)

    if len(encoder.classes_) < 2:
        raise ValueError("Training requires at least two distinct labels.")

    # ========================================================
    # TRAIN ON ALL LABELED DATA
    # ========================================================
    model = XGBClassifier(
        objective="multi:softprob",
        num_class=len(encoder.classes_),
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )

    print("\n========== TRAINING ==========")
    model.fit(X, y)

    # Training accuracy is diagnostic only, not unseen-dashboard accuracy.
    predictions = model.predict(X)
    accuracy = accuracy_score(y, predictions)

    print(f"\nTraining accuracy: {accuracy * 100:.2f}%")
    print("\nTraining classification report:")
    print(
        classification_report(
            y,
            predictions,
            labels=list(range(len(encoder.classes_))),
            target_names=encoder.classes_,
            zero_division=0,
        )
    )

    print("Training confusion matrix:")
    print(confusion_matrix(y, predictions).tolist())

    # ========================================================
    # SAVE MODEL + ENCODER + FEATURE METADATA
    # ========================================================

    model_path = MODEL_DIR / "model.json"
    encoder_path = MODEL_DIR / "label_encoder.pkl"
    medians_path = MODEL_DIR / "feature_medians.pkl"
    metadata_path = MODEL_DIR / "metadata.json"

    model.save_model(str(model_path))

    with open(encoder_path, "wb") as f:
        pickle.dump(encoder, f)

    with open(medians_path, "wb") as f:
        pickle.dump(medians.to_dict(), f)

    metadata = {
        "feature_columns": FEATURE_COLUMNS,
        "label_classes": encoder.classes_.tolist(),
        "training_rows": int(len(df)),
        "dashboard_count": int(df["dashboard_id"].nunique()),
        "training_accuracy": float(accuracy),
        "csv_path": str(DATA_PATH),
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\n========== SAVED ==========")
    print(f"Model:   {model_path}")
    print(f"Encoder: {encoder_path}")
    print(f"Medians: {medians_path}")
    print(f"Metadata:{metadata_path}")
    print("\nTraining completed successfully.")


if __name__ == "__main__":
    main()
