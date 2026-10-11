
import json
import sys
import joblib
import pandas as pd

from pathlib import Path
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.features.extract_features import calculate_features

CANDIDATE_FILE = ROOT / "dataset" / "new_candidates" / "new_dashboard_candidates.json"
MODEL_FILE = ROOT / "models" / "xgboost_model.json"
ENCODER_FILE = ROOT / "models" / "label_encoder.pkl"
OUTPUT_FILE = ROOT / "dataset" / "new_candidates" / "new_dashboard_predictions.json"

FEATURE_COLS = [
    "width", "height", "area", "aspect_ratio", "child_count",
    "text_count", "numeric_text_count", "text_density",
    "numeric_density", "vector_count", "line_count",
    "ellipse_count", "rectangle_count", "graphical_count",
    "has_percentage", "has_date_text", "has_chart_word",
    "has_table_word", "has_kpi_word", "has_filter_word",
]


def main():
    print("=" * 60)
    print("XGBOOST PREDICTION")
    print("=" * 60)

    with open(CANDIDATE_FILE, "r", encoding="utf-8") as f:
        candidate_data = json.load(f)

    if isinstance(candidate_data, list):
        candidates = candidate_data
    else:
        candidates = candidate_data.get("candidates", [])

    if not candidates:
        print("No candidates found. Check the candidate JSON structure.")
        return

    print(f"Candidates found: {len(candidates)}")

    print("\nLoading XGBoost model...")
    model = XGBClassifier()
    model.load_model(str(MODEL_FILE))

    print("Loading label encoder...")
    encoder = joblib.load(ENCODER_FILE)
    print("Classes:", list(encoder.classes_))

    feature_rows = [
        calculate_features(candidate)
        for candidate in candidates
    ]

    features_df = pd.DataFrame(feature_rows)
    X_new = features_df[FEATURE_COLS]

    print(f"\nFeature matrix shape: {X_new.shape}")

    predictions_encoded = model.predict(X_new)
    predictions = encoder.inverse_transform(
        predictions_encoded.astype(int)
    )

    results = []

    for candidate, prediction in zip(candidates, predictions):
        result = dict(candidate)
        result["predicted_type"] = str(prediction)
        results.append(result)

        print(
            f"{candidate.get('name', 'Unnamed')} "
            f"| {candidate.get('id', 'No ID')} "
            f"| {prediction}"
        )

    output_data = {
        "source": str(CANDIDATE_FILE.relative_to(ROOT)),
        "candidate_count": len(results),
        "predictions": results,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("PREDICTION COMPLETE")
    print(f"Saved to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
