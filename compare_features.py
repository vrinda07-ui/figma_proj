import pandas as pd

original = pd.read_csv("dataset/features/component_features.csv", dtype=str)
claude = pd.read_csv("claude_component_features.csv", dtype=str)

key = ["dashboard_id", "candidate_id"]

print("ORIGINAL rows:", len(original))
print("CLAUDE rows:", len(claude))
print("Original columns match:", list(original.columns) == list(claude.columns))
print("Original duplicate IDs:", original.duplicated(key).sum())
print("Claude duplicate IDs:", claude.duplicated(key).sum())

a = original.drop_duplicates(key).set_index(key)
b = claude.drop_duplicates(key).set_index(key)

print("Missing from Claude:", len(a.index.difference(b.index)))
print("Extra in Claude:", len(b.index.difference(a.index)))

common = a.index.intersection(b.index)
cols = [c for c in original.columns if c not in key]
changed = []

for idx in common:
    for col in cols:
        x, y = a.loc[idx, col], b.loc[idx, col]
        if pd.isna(x) and pd.isna(y):
            continue
        try:
            same = abs(float(x) - float(y)) < 1e-6
        except (ValueError, TypeError):
            same = str(x).strip() == str(y).strip()
        if not same:
            changed.append((idx, col, x, y))

print("Changed values:", len(changed))
for item in changed[:30]:
    print(item)

print("\nClaude dashboard IDs:")
print(claude["dashboard_id"].value_counts().to_string())

print("\nDone. Only the first 30 changed values are displayed.")
