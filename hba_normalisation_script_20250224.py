import pandas as pd
import re

# Define input and output file names
input_csv = "sr_hba_sv_carier.sample_interval_summary.csv"
input_csv = "hba_long_read_control.txt"
output_excel = "normalised_long_read_control_20250310.xlsx"

# Load the CSV file
df = pd.read_csv(input_csv)

# Base columns to keep
base_cols = ["Target"]
# Identify sample mean coverage columns
mean_cvg_cols = [col for col in df.columns if col.endswith("_mean_cvg")]

# Function to extract sample ID using first character + 7 numeric characters or full sample name prefix
def extract_sample_id(sample_name):
    match = re.match(r"([A-Z]\d{7})", sample_name)
    if match:
        return match.group(1)
    else:
        # Extract full sample name prefix before the first underscore or dash
        return re.split(r"[-_]", sample_name)[0]

# Extract sample IDs from column names
sample_ids = {col: extract_sample_id(col) for col in mean_cvg_cols}

# Create a dictionary with the provided sample labels
sample_labels = {
    "A0002492": "SEA",
    "C0001552": "SEA",
    "A0002490": "SEA",
    "B0011392": "SEA",
    "A0011911": "SEA",
    "B0004059": "SEA",
    "B0004333": "SEA",
    "B0011015": "SEA",
    "A0019487": "SEA",
    "B0013387": "SEA",
    "B0013385": "SEA",
    "A0038972": "SEA",
    "B0004060": "SEA",
    "A0019818": "SEA",
    "B0004942": "SEA",
    "B0011013": "SEA",
    "C0001841": "SEA",
    "B0016626": "SEA",
    "A0038971": "SEA",
    "A0011913": "SEA",
    "BT016753B01": "SEA",  # Updated to match full sample name prefix
    "B0015307": "4.2K",
    "B0012588": "4.2K",
    "B0015306": "4.2K",
    "B0004968": "4.2K",
    "B0021131": "3.7K",
    "B0009972": "3.7K",
    "B0000799": "3.7K",
    "C0011401": "3.7K",
    "B0013808": "3.7K",
    "C0024118": "3.7K",
    "B0011444": "3.7K",
    "B0010890": "3.7K",
    "B0009971": "3.7K",
    "B0009973": "3.7K",
    "B0000796": "3.7K",
    "C0011156": "3.7K",
    "B0011433": "3.7K",
    "B0021069": "3.7K",
    "B0011434": "3.7K",
    "A1010296": "3.7K",
    "B0012303": "3.7K",
    "B0011390": "3.7K",
    "C0011400": "3.7K",
    "B0013812": "3.7K"
}


renamed_columns = {
    col: f"{sample_id}_{sample_labels.get(sample_id, 'Control')}"
    for col, sample_id in sample_ids.items()
}

final_cols = base_cols + mean_cvg_cols

df_filtered = df[final_cols]

df_filtered.rename(columns=renamed_columns, inplace=True)

# Retrieve the normalization values from row where Target == "chr16:90001-290000"
normalization_values = df_filtered[df_filtered["Target"] == "chr16:90001-290000"].iloc[:, 3:].values.flatten()

# Apply normalization correctly by dividing each row by the respective sample's normalization value
df_normalized = df_filtered.copy()
#df_normalized.iloc[:, 3:] = df_filtered.iloc[:, 3:].div(normalization_values, axis=1)
df_normalized.iloc[:, 1:] = df_filtered.iloc[:, 1:].div(normalization_values, axis=1)

# Save results to an Excel file with separate sheets
with pd.ExcelWriter(output_excel) as writer:
    df_filtered.to_excel(writer, sheet_name="Raw Coverage", index=False)
    df_normalized.to_excel(writer, sheet_name="Normalized Coverage", index=False)


import matplotlib.pyplot as plt
import pandas as pd
import numpy as np