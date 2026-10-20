
import json
import pickle
import importlib.util
from pathlib import Path

import pandas as pd
from xgboost import XGBClassifier


ROOT = Path(__file__).resolve().parent

RAW_JSON = ROOT / "dataset" / "new_dashboard" / "figma_data.json"
CANDIDATES_JSON = ROOT / "dataset" / "candidates" / "figma_data_candidates.json"

MODEL_DIR = ROOT / "models" / "xgboost_labeled"
OUTPUT_DIR = ROOT / "outputs" / "new_dashboard_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "model.json"
ENCODER_PATH = MODEL_DIR / "label_encoder.pkl"
MEDIANS_PATH = MODEL_DIR / "feature_medians.pkl"
METADATA_PATH = MODEL_DIR / "metadata.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load Python module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    # Check required files.
    for path in [RAW_JSON, MODEL_PATH, ENCODER_PATH,
                 MEDIANS_PATH, METADATA_PATH]:
        if not path.exists():
            raise FileNotFoundError(f"Required file not found:\n{path}")

    print("Loading candidate generator...")
    generator = load_module(
        "candidate_generator",
        ROOT / "src" / "preprocessing" / "generate_candidates.py"
    )

    print("Loading feature extractor...")
    feature_module = load_module(
        "feature_extractor",
        ROOT / "src" / "features" / "extract_features.py"
    )

    # Generate candidates for this dashboard only.
    print(f"\nProcessing dashboard: {RAW_JSON.name}")
    generator.generate_dashboard(str(RAW_JSON))

    if not CANDIDATES_JSON.exists():
        raise FileNotFoundError(
            f"Candidate file was not created:\n{CANDIDATES_JSON}"
        )

    with open(CANDIDATES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        candidates = data.get("candidates", [])
    else:
        candidates = []

    if not candidates:
        raise ValueError(
            "No candidates found. Check the generated candidate JSON "
            "and the candidate-generation rules."
        )

    print(f"Candidates found: {len(candidates)}")

    # Extract the same features used during training.
    feature_rows = [
        feature_module.calculate_features(candidate)
        for candidate in candidates
    ]

    features = pd.DataFrame(feature_rows)

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    feature_columns = metadata["feature_columns"]

    missing = [c for c in feature_columns if c not in features.columns]
    if missing:
        raise ValueError(f"Feature extractor is missing columns: {missing}")

    X = features[feature_columns].copy()

    for col in feature_columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    with open(MEDIANS_PATH, "rb") as f:
        medians = pickle.load(f)

    X = X.fillna(pd.Series(medians)).fillna(0)

    # Load the already-trained model. This does NOT retrain it.
    model = XGBClassifier()
    model.load_model(str(MODEL_PATH))

    with open(ENCODER_PATH, "rb") as f:
        encoder = pickle.load(f)

    predicted_ids = model.predict(X).astype(int)
    predicted_labels = encoder.inverse_transform(predicted_ids)
    probabilities = model.predict_proba(X)
    confidence = probabilities.max(axis=1) * 100

    # Build readable results.
    results = pd.DataFrame({
        "candidate_id": [
            c.get("candidate_id", "") for c in candidates
        ],
        "component_name": [
            c.get("name", c.get("component_name", "")) for c in candidates
        ],
        "component_type": [
            c.get("type", "") for c in candidates
        ],
        "width": [
            c.get("width", None) for c in candidates
        ],
        "height": [
            c.get("height", None) for c in candidates
        ],
        "predicted_label": predicted_labels,
        "confidence_percent": confidence.round(2),
    })

    csv_path = OUTPUT_DIR / "predictions.csv"
    json_path = OUTPUT_DIR / "predictions.json"

    results.to_csv(csv_path, index=False, encoding="utf-8-sig")
    results.to_json(
        json_path, orient="records", indent=2, force_ascii=False
    )

    print("\n========== PREDICTIONS ==========")
    print(results.to_string(index=False))
    print(f"\nCSV saved to:  {csv_path}")
    print(f"JSON saved to: {json_path}")
    print("\nTesting completed. The model was not retrained.")


if __name__ == "__main__":
    main()
