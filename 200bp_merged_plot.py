import pandas as pd
import matplotlib.pyplot as plt

# Define common axis limits
xlims = (0, 2)
ylims = (0, 2.5)

# List of labels to include
wanted = ['3.7K', '4.2K', 'SEA', 'CONTROL']

# ----------------------------
# Process First Dataset
# ----------------------------
df1 = pd.read_excel('200bp_new_run.xlsx', sheet_name='200bp_new_run')

# Save rows with mean_r1 or mean_r2 > 1.25
filtered_rows1 = df1[(df1['mean_r1'] > 1.25) | (df1['mean_r2'] > 1.25)]
filtered_rows1.to_excel('filtered_output_full_df.xlsx', index=False)

# Filter and drop NA values
df_sel1 = df1[df1['First label'].isin(wanted)].dropna(subset=['mean_r1', 'mean_r2'])
n1 = len(df_sel1)

# Plot 1: First dataset, colored by First label
plt.figure(figsize=(8, 6))
for lbl in df_sel1['First label'].unique():
    sub = df_sel1[df_sel1['First label'] == lbl]
    plt.scatter(sub['mean_r1'], sub['mean_r2'], label=lbl, alpha=0.7)
plt.xlabel('mean_r1')
plt.ylabel('mean_r2')
plt.title(f'First Labels in {{3.7K,4.2K,SEA, CONTROL}} (n={n1})')
plt.legend(title='First Label', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xlim(*xlims)
plt.ylim(*ylims)
plt.tight_layout()
plt.show()

# Plot 2: First dataset, colored by Final label
plt.figure(figsize=(8, 6))
for lbl in df_sel1['final_label'].unique():
    sub = df_sel1[df_sel1['final_label'] == lbl]
    plt.scatter(sub['mean_r1'], sub['mean_r2'], label=lbl, alpha=0.7)
plt.xlabel('mean_r1')
plt.ylabel('mean_r2')
plt.title(f'Final Labels in {{3.7K,4.2K,SEA, CONTROL}} (n={n1})')
plt.legend(title='Final Label', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xlim(*xlims)
plt.ylim(*ylims)
plt.tight_layout()
plt.show()

# ----------------------------
# Process Second Dataset
# ----------------------------
df2 = pd.read_excel('200bp_new_run.xlsx', sheet_name='1684_lr')

# Save rows with mean_r1 or mean_r2 > 1.25
filtered_rows2 = df2[(df2['mean_r1'] > 1.25) | (df2['mean_r2'] > 1.25)]
filtered_rows2.to_excel('1684_above_125r1r2_df.xlsx', index=False)

# Filter and drop NA values
df_sel2 = df2[df2['First label'].isin(wanted)].dropna(subset=['mean_r1', 'mean_r2'])
n2 = len(df_sel2)

# Plot 3: Second dataset, colored by First label
plt.figure(figsize=(8, 6))
for lbl in df_sel2['First label'].unique():
    sub = df_sel2[df_sel2['First label'] == lbl]
    plt.scatter(sub['mean_r1'], sub['mean_r2'], label=lbl, alpha=0.7)
plt.xlabel('mean_r1')
plt.ylabel('mean_r2')
plt.title(f'1684_lr: First Labels in {{3.7K,4.2K,SEA, CONTROL}} (n={n2})')
plt.legend(title='First Label', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xlim(*xlims)
plt.ylim(*ylims)
plt.tight_layout()
plt.show()