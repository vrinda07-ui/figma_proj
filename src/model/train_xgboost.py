
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.utils.class_weight import compute_sample_weight


DATA_FILE = "dataset/features/training_dataset.csv"

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

# Load dataset
df = pd.read_csv(DATA_FILE)

# Remove FILTER for now; there is only one labeled example.
df = df[df["label"].isin(["KPI_CARD", "CHART", "TABLE", "OTHER"])].copy()
df = df.dropna(subset=FEATURE_COLS + ["label"]).reset_index(drop=True)

X = df[FEATURE_COLS].astype(float)
y = df["label"].astype(str)

# Create one consistent mapping for all classes.
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

print("Classes:", list(encoder.classes_))
print("Class counts:")
print(y.value_counts().to_string())
print("Samples:", len(df))
print("Features:", len(FEATURE_COLS))

# Each class must have enough samples for 3-fold stratified CV.
class_counts = y.value_counts()
if class_counts.min() < 3:
    raise ValueError(
        "Every class needs at least 3 examples for 3-fold "
        "stratified cross-validation.\n" + class_counts.to_string()
    )

skf = StratifiedKFold(
    n_splits=3,
    shuffle=True,
    random_state=42
)

accuracies = []
f1_scores = []

print("\n===== 3-FOLD CROSS VALIDATION =====")

for fold, (train_idx, test_idx) in enumerate(skf.split(X, y_encoded), 1):

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train_original = y.iloc[train_idx]
    y_test_original = y.iloc[test_idx]

    # Encode using the same fixed mapping as the complete dataset.
    # StratifiedKFold should keep all classes in each training fold.
    y_train = encoder.transform(y_train_original)
    y_test = encoder.transform(y_test_original)

    weights = compute_sample_weight(
        class_weight="balanced",
        y=y_train
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
        random_state=42
    )

    model.fit(
        X_train,
        y_train,
        sample_weight=weights
    )

    predictions = model.predict(X_test).astype(int)

    print(f"\n===== FOLD {fold} REPORT =====")
    print(
        classification_report(
            y_test,
            predictions,
            labels=np.arange(len(encoder.classes_)),
            target_names=encoder.classes_,
            zero_division=0
        )
    )

    accuracy = accuracy_score(y_test, predictions)
    macro_f1 = f1_score(
        y_test,
        predictions,
        labels=np.arange(len(encoder.classes_)),
        average="macro",
        zero_division=0
    )

    accuracies.append(accuracy)
    f1_scores.append(macro_f1)

    print(f"Fold {fold} Accuracy : {accuracy:.4f}")
    print(f"Fold {fold} Macro F1 : {macro_f1:.4f}")

print("\n===== FINAL CROSS-VALIDATION RESULTS =====")
print(f"Average Accuracy : {np.mean(accuracies):.4f}")
print(f"Average Macro F1 : {np.mean(f1_scores):.4f}")

# Train the final model on the complete four-class dataset.
final_weights = compute_sample_weight(
    class_weight="balanced",
    y=y_encoded
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
    random_state=42
)

final_model.fit(
    X,
    y_encoded,
    sample_weight=final_weights
)

MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

final_model.save_model(str(MODEL_DIR / "xgboost_model.json"))
joblib.dump(encoder, MODEL_DIR / "label_encoder.pkl")

print("\nModel saved successfully.")
print("Model:", MODEL_DIR / "xgboost_model.json")
print("Encoder:", MODEL_DIR / "label_encoder.pkl")

# Feature importance
importance = pd.DataFrame({
    "feature": FEATURE_COLS,
    "importance": final_model.feature_importances_
}).sort_values("importance", ascending=False)

print("\n===== FEATURE IMPORTANCE =====")
print(importance.to_string(index=False))
