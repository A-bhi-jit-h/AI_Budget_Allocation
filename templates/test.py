import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor

# -----------------------------
# 1. Load Dataset
# -----------------------------
file_path = r"C:\Users\Asus\Downloads\ward_budget_dataset_101_wards_realistic.csv"
df = pd.read_csv(file_path)

# -----------------------------
# 2. Feature Selection
# -----------------------------
budget_cols = [col for col in df.columns if col.startswith("budget_")]

features = (
    budget_cols +
    [
        "prev_year_actual_expenditure",
        "unspent_amount"
    ]
)

target = "prev_year_allocated_budget"

X = df[features]
y = df[target]

# -----------------------------
# 3. Train-Test Split
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# -----------------------------
# 4. Train XGBoost Model
# -----------------------------
model = XGBRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42
)

model.fit(X_train, y_train)

# -----------------------------
# 5. Model Evaluation
# -----------------------------
y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("Model Performance:")
print(f"MAE  : ₹{mae:,.0f}")
print(f"R²   : {r2:.3f}")

# -----------------------------
# 6. Predict Next Year Budget
# -----------------------------
# Assume next year's features ≈ last known values
latest_data = X.copy()

next_year_budget_prediction = model.predict(latest_data)

df["predicted_budget_next_year"] = next_year_budget_prediction.astype(int)

# -----------------------------
# 7. Save Predictions
# -----------------------------
output_path = r"C:\Users\Asus\Downloads\ward_budget_dataset_101_wards_realistic1.csv"
df.to_csv(output_path, index=False)

print("\nPrediction completed.")
print(f"Predicted budgets saved to:\n{output_path}")