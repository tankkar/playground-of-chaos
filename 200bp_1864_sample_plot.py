import pandas as pd
import matplotlib.pyplot as plt

# Load data
#df = pd.read_excel('lr_validation_result_20250617.copy.xlsx', sheet_name='1684_lr')
#df = pd.read_csv("200bp_new_run.csv")
df = pd.read_excel('200bp_new_run.xlsx', sheet_name='1684_lr')

# Filter rows where mean_r1 or mean_r2 > 1.25 (unchanged)
filtered_rows = df[(df['mean_r1'] > 1.25) | (df['mean_r2'] > 1.25)]
filtered_rows.to_excel('1684_above_125r1r2_df.xlsx', index=False)

# Exact-match filter for wanted First labels
wanted = ['3.7K', '4.2K', 'SEA', 'CONTROL']
df_sel = df[df['First label'].isin(wanted)]

# Remove rows with missing values in mean_r1 or mean_r2
df_sel = df_sel.dropna(subset=['mean_r1', 'mean_r2'])

# Get total number of valid data points
n = len(df_sel)

# 2D Scatter Plot: color by First label
plt.figure(figsize=(8, 6))
for lbl in df_sel['First label'].unique():
    sub = df_sel[df_sel['First label'] == lbl]
    plt.scatter(sub['mean_r1'], sub['mean_r2'], label=lbl, alpha=0.7)

plt.xlabel('mean_r1')
plt.ylabel('mean_r2')
plt.title(f'First Labels in {{3.7K,4.2K,SEA,CONTROL}} (n={n})')
plt.legend(title='First Label', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()