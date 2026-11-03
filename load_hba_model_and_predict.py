import joblib
import pandas as pd
import re

# Load model and original data
model = joblib.load("trained_random_forest_model.pkl")
X_original = pd.read_csv("real_predicted_data.csv")
print(X_original.shape)
# Preprocess data for prediction
columns_to_drop = ["Unnamed: 0", "group", "sampleid"]
X_new = X_original.drop(columns=columns_to_drop, errors="ignore")
X_new = X_new.T
intervals_to_remove = [
    (153200, 154400),
    (160000, 165000),
    (172000, 173400),
    (176200, 177000),
]

cols_to_remove = []
for col in X_new.columns:
    match = re.match(r"chr16:(\d+)-(\d+)", col)
    if match:
        start, end = map(int, match.groups())
        for (rstart, rend) in intervals_to_remove:
            if not (end < rstart or start > rend):
                cols_to_remove.append(col)
                break

X_filtered = X_new.drop(columns=cols_to_remove, errors="ignore")

predicted_labels = model.predict(X_filtered)
predicted_probabilities = model.predict_proba(X_filtered)

# Add prediction results to the original data
X_original["predicted_label"] = predicted_labels
probability_columns = [f"prob_{cls}" for cls in model.classes_]
X_original[probability_columns] = pd.DataFrame(
    predicted_probabilities,
    index=X_original.index
)

# --- Integrate second-level classification ---
# Define region groups (ensure these column names match your normalized data)
region1_cols = [
    "chr16:170201-170400", "chr16:170401-170600", "chr16:170601-170800",
    "chr16:170801-171000", "chr16:171001-171200", "chr16:171201-171400",
    "chr16:171401-171600", "chr16:171601-171800", "chr16:171801-172000",
    "chr16:172001-172200", "chr16:172201-172400"
]
region2_cols = [
    "chr16:173329-173471", "chr16:173471-173710", "chr16:173711-173910",
    "chr16:173911-174110", "chr16:174111-174310", "chr16:174311-174510",
    "chr16:174511-174710", "chr16:174711-174910", "chr16:174911-175110",
    "chr16:175111-175310", "chr16:175311-175510", "chr16:175511-175710"
]

region_sea_cols = []
for col in X_original.columns:
    if col in ["sampleid", "group", "predicted_label"] + probability_columns:
        continue
    m = re.match(r"chr16:(\d+)-(\d+)", col)
    if m:
        start, end = map(int, m.groups())
        if start >= 164800 and end <= 184700:
            region_sea_cols.append(col)

threshold_value = 0.05
required_fraction_sea = 0.50 
required_fraction_other = 0.20  

def second_classification(row):
    label = row["predicted_label"]
    if "SEA" in label:
        new_label = label
        if region_sea_cols:
            frac_sea = (row[region_sea_cols] < threshold_value).mean()
            if frac_sea > required_fraction_sea:
                new_label = "SEA homozygous deletion"
        frac_r1 = (row[region1_cols] < threshold_value).mean()
        if frac_r1 > required_fraction_other:
            if new_label != "SEA homozygous deletion":
                new_label += " + 4.2K"
            else:
                new_label = "SEA homozygous deletion + 3.7K homozygous"
        frac_r2 = (row[region2_cols] < threshold_value).mean()
        if frac_r2 > required_fraction_other:
            if new_label != "SEA homozygous deletion":
                new_label += " + 3.7K"
            else:
                new_label = "SEA homozygous deletion + 4.2K homozygous"
        return new_label
    else:
        return label

X_original["final_label"] = X_original.apply(second_classification, axis=1)

X_original.to_csv("predicted_data_with_labels-20250331.csv", index=False)
