import pandas as pd
import re

# Define input and output file names
input_csv = "hba_long_read_control.txt"
#####input_csv = "new_input_for_training.txt"
#input_csv="hba_real_data_normalized.tsv"
input_csv="merged_all_batches_interval_summary.tsv"
output_excel = "normalised_long_read_control_20250327.xlsx"
label = 'label.csv'

label = pd.read_csv(label)
df = pd.read_csv(input_csv,sep='\t')

base_cols = ["Target"]

mean_cvg_cols = [col for col in df.columns if col.endswith("_mean_cvg")]


def extract_sample_id(sample_name):
    match = re.match(r"([A-Z]\d{7})", sample_name)
    if match:
        return match.group(1)
    else:
        return re.split(r"[-_]", sample_name)[0]

sample_ids = {col: extract_sample_id(col) for col in mean_cvg_cols}
final_cols = base_cols + mean_cvg_cols
df_filtered = df[final_cols]

normalization_values = df_filtered[df_filtered["Target"] == "chr16:90001-290000"].iloc[:, 1:].values.flatten()

# Create a copy of the filtered dataframe for normalization
df_normalized = df_filtered.copy()
print(df_normalized)

df_normalized.iloc[:, 1:] = df_filtered.iloc[:, 1:].div(normalization_values, axis=1)
df_normalized = df_normalized.T
df_normalized.columns = df_normalized.loc['Target']
df_normalized = df_normalized.drop('Target')
df_normalized = df_normalized.drop(columns=[
    "chr16:90001-290000",
    "chr16:177523-290000"
], errors="ignore")  # 'errors="ignore"' avoids crashing if a column is missing

print(df_normalized)


df_normalized['sampleid'] = df_normalized.index.str.split('-').str[0]
label_map = label.set_index('sampleid')['group'].to_dict()
df_normalized['group'] = df_normalized['sampleid'].map(label_map).fillna("CONTROL")
df_normalized.head()
df_normalized.to_csv('normalized_transposed_at_risk_children.csv')


###################################Machine learning, Random forest ###################################
import re
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.metrics import confusion_matrix, classification_report, f1_score

intervals_to_remove = [
    (153200, 154400),
    (160000, 165000),
    (172000, 173400),
    (176200, 177000),
]

cols_to_remove = []

for col in df_normalized.columns:
    # Skip non-coverage columns like 'sampleid' or 'group'
    if col in ["sampleid", "group"]:
        continue
    
    # Columns are named like "chr16:160001-160200"
    match = re.match(r"chr16:(\d+)-(\d+)", col)
    if match:
        start, end = map(int, match.groups())  
        for (rstart, rend) in intervals_to_remove:
            if not (end < rstart or start > rend):
                cols_to_remove.append(col)
                break  

df_filtered = df_normalized.drop(columns=cols_to_remove, errors="ignore")


print("Removed columns:", cols_to_remove)
print("Remaining columns:", df_filtered.columns)


X = df_filtered.drop(["sampleid", "group"], axis=1)
y = df_filtered["group"]

clf = RandomForestClassifier(n_estimators=100, random_state=42)

#########
skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
scores = cross_val_score(clf, X, y, cv=skf, scoring="accuracy")

print("Cross-validation accuracies:", scores)
print("Mean accuracy:", np.mean(scores))



# 1) Get predictions via cross_val_predict
y_pred = cross_val_predict(clf, X, y, cv=skf)

# 2) Compute confusion matrix
cm = confusion_matrix(y, y_pred)
print("Confusion Matrix:\n", cm)


print("Classification Report:")
print(classification_report(y, y_pred))

macro_f1 = f1_score(y, y_pred, average="macro")
weighted_f1 = f1_score(y, y_pred, average="weighted")

print("Macro-average F1:", macro_f1)
print("Weighted-average F1:", weighted_f1)

df_results = pd.DataFrame({
    "Sample": X.index,     # or, if you have sample IDs in X, adapt as needed
    "True Label": y.values,
    "Predicted Label": y_pred
})

# Determine if each sample was correct
df_results["Correct?"] = (df_results["True Label"] == df_results["Predicted Label"])

#######################################################

import re
import pandas as pd

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
for col in df_normalized.columns:
    if col in ["sampleid", "group"]:
        continue
    m = re.match(r"chr16:(\d+)-(\d+)", col)
    if m:
        start, end = map(int, m.groups())
        if start >= 164800 and end <= 184700:
            region_sea_cols.append(col)

threshold_value = 0.05
required_fraction = 0.20

def reclassify_homo(row):
    if row["group"] == "SEA":
        new_label = row["group"]
        if region_sea_cols:
            frac_sea = (row[region_sea_cols] < threshold_value).mean()
            if frac_sea > required_fraction:
                new_label = "SEA homozygous deletion"
        frac_r1 = (row[region1_cols] < threshold_value).mean()
        if frac_r1 > required_fraction:
            if new_label != row["group"]:
                new_label += " + 3.7K homozygous"
            else:
                new_label = "SEA + 3.7K homozygous"
        frac_r2 = (row[region2_cols] < threshold_value).mean()
        if frac_r2 > required_fraction:
            if new_label != row["group"]:
                new_label += " + 4.2K homozygous"
            else:
                new_label = "SEA + 4.2K homozygous"
        return new_label
    else:
        return row["group"]

df_normalized["group"] = df_normalized.apply(reclassify_homo, axis=1)
print(df_normalized[["group"]].head())
