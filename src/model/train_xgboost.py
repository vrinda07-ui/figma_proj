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

X = df[FEATURE_COLS]
y = df["label"]

# Convert labels to numbers
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

print("Classes:", list(encoder.classes_))
print("Samples:", len(df))
print("Features:", len(FEATURE_COLS))

# 3-fold stratified cross-validation
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

    y_train = y_encoded[train_idx]
    y_test = y_encoded[test_idx]

    # Balance minority classes
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
        objective="multi:softmax",
        num_class=len(encoder.classes_),
        eval_metric="mlogloss",
        random_state=42
    )

    model.fit(
        X_train,
        y_train,
        sample_weight=weights
    )

    predictions = model.predict(X_test)
    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=range(len(encoder.classes_)),
            target_names=encoder.classes_,
            zero_division=0
        )
    )

    accuracy = accuracy_score(y_test, predictions)
    macro_f1 = f1_score(
        y_test,
        predictions,
        average="macro"
    )

    accuracies.append(accuracy)
    f1_scores.append(macro_f1)

    print(f"\nFold {fold}")
    print(f"Accuracy : {accuracy:.4f}")
    print(f"Macro F1 : {macro_f1:.4f}")

print("\n===== FINAL RESULTS =====")

print(
    f"Average Accuracy : "
    f"{np.mean(accuracies):.4f}"
)

print(
    f"Average Macro F1 : "
    f"{np.mean(f1_scores):.4f}"
)


# Train final model on complete dataset
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
    objective="multi:softmax",
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

final_model.save_model(MODEL_DIR / "xgboost_model.json")

joblib.dump(
    encoder,
    MODEL_DIR / "label_encoder.pkl"
)

print("\nModel saved successfully.")
print("Model:", MODEL_DIR / "xgboost_model.json")
print("Encoder:", MODEL_DIR / "label_encoder.pkl")

# Feature importance
importance = pd.DataFrame({
    "feature": FEATURE_COLS,
    "importance": final_model.feature_importances_
}).sort_values(
    "importance",
    ascending=False
)

print("\n===== FEATURE IMPORTANCE =====")
print(importance.to_string(index=False))