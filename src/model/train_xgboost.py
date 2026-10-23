
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.utils.class_weight import compute_sample_weight

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DATA_FILE = Path(
    "dataset/features/component_features_labeled copy.csv"
)

MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_LABELS = [
    "KPI_CARD",
    "CHART",
    "TABLE",
    "FILTER",
    "NAVBAR",
    "HEADER",
    "OTHER",
]

FEATURE_COLS = [
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

# --------------------------------------------------
# 1. LOAD LABELED COMPONENT FEATURES
# --------------------------------------------------

if not DATA_FILE.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_FILE}\n"
        "Place component_features_labeled.csv in "
        "dataset/features/."
    )

df = pd.read_csv(DATA_FILE)

required_cols = FEATURE_COLS + [
    "dashboard_id",
    "candidate_id",
    "label",
]

missing_cols = set(required_cols) - set(df.columns)

if missing_cols:
    raise ValueError(
        f"Missing required columns: {sorted(missing_cols)}"
    )

print("Original dataset shape:", df.shape)

# Keep only supported, non-empty labels.
df["label"] = df["label"].astype("string").str.strip()

df = df[
    df["label"].isin(SUPPORTED_LABELS)
].copy()

# Convert features to numeric values.
for col in FEATURE_COLS:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Remove rows with missing labels or features.
df = df.dropna(
    subset=FEATURE_COLS + ["label"]
).reset_index(drop=True)

if df.empty:
    raise ValueError("No valid labeled training rows found.")

# Check that the features are finite.
if not np.isfinite(
    df[FEATURE_COLS].to_numpy(dtype=float)
).all():
    raise ValueError("Features contain infinite values.")

X = df[FEATURE_COLS].astype(float)
y = df["label"].astype(str)

# --------------------------------------------------
# 2. CHECK LABEL DISTRIBUTION
# --------------------------------------------------

print("\n===== DATASET SUMMARY =====")
print("Labeled samples:", len(df))
print("Number of features:", len(FEATURE_COLS))
print("\nClass counts:")
print(y.value_counts().to_string())

class_counts = y.value_counts()

if len(class_counts) < 2:
    raise ValueError("At least two classes are required.")

if class_counts.min() < 3:
    raise ValueError(
        "Every included class needs at least 3 examples "
        "for 3-fold stratified CV.\n"
        + class_counts.to_string()
    )

# --------------------------------------------------
# 3. ENCODE LABELS
# --------------------------------------------------

encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

print("\nEncoded classes:", list(encoder.classes_))

# --------------------------------------------------
# 4. THREE-FOLD CROSS-VALIDATION
# --------------------------------------------------

skf = StratifiedKFold(
    n_splits=3,
    shuffle=True,
    random_state=42,
)

accuracies = []
macro_f1_scores = []

print("\n===== 3-FOLD CROSS-VALIDATION =====")

for fold, (train_idx, test_idx) in enumerate(
    skf.split(X, y_encoded), start=1
):
    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train = y_encoded[train_idx]
    y_test = y_encoded[test_idx]

    weights = compute_sample_weight(
        class_weight="balanced",
        y=y_train,
    )

    model = XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        num_class=len(encoder.classes_),
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
        sample_weight=weights,
    )

    predictions = model.predict(X_test).astype(int)

    accuracy = accuracy_score(y_test, predictions)

    macro_f1 = f1_score(
        y_test,
        predictions,
        average="macro",
        zero_division=0,
    )

    accuracies.append(accuracy)
    macro_f1_scores.append(macro_f1)

    print(f"\n===== FOLD {fold} =====")

    print(
        classification_report(
            y_test,
            predictions,
            labels=np.arange(len(encoder.classes_)),
            target_names=encoder.classes_,
            zero_division=0,
        )
    )

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")

print("\n===== CROSS-VALIDATION RESULTS =====")
print(f"Mean accuracy: {np.mean(accuracies):.4f}")
print(f"Accuracy std:  {np.std(accuracies):.4f}")
print(f"Mean macro F1: {np.mean(macro_f1_scores):.4f}")

# --------------------------------------------------
# 5. TRAIN FINAL MODEL ON ALL LABELED ROWS
# --------------------------------------------------

final_weights = compute_sample_weight(
    class_weight="balanced",
    y=y_encoded,
)

final_model = XGBClassifier(
    n_estimators=150,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="multi:softprob",
    num_class=len(encoder.classes_),
    eval_metric="mlogloss",
    random_state=42,
    n_jobs=-1,
)

final_model.fit(
    X,
    y_encoded,
    sample_weight=final_weights,
)

# --------------------------------------------------
# 6. SAVE MODEL AND ENCODER
# --------------------------------------------------

model_path = MODEL_DIR / "xgboost_model.json"
encoder_path = MODEL_DIR / "label_encoder.pkl"

final_model.save_model(str(model_path))
joblib.dump(encoder, encoder_path)

print("\n===== MODEL SAVED =====")
print("Model:", model_path)
print("Encoder:", encoder_path)

# --------------------------------------------------
# 7. FEATURE IMPORTANCE
# --------------------------------------------------

importance = pd.DataFrame({
    "feature": FEATURE_COLS,
    "importance": final_model.feature_importances_,
}).sort_values(
    "importance",
    ascending=False,
)

print("\n===== FEATURE IMPORTANCE =====")
print(importance.to_string(index=False))

importance.to_csv(
    MODEL_DIR / "feature_importance.csv",
    index=False,
)

print("\nTraining pipeline completed.")
