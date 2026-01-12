import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Define common axis limits
xlims = (-0.1, 2)
ylims = (-0.1, 2.5)

# Generate tick marks starting from 0
xticks = np.arange(0, xlims[1] + 0.1, 0.5)
yticks = np.arange(0, ylims[1] + 0.1, 0.5)

# Fixed colors for consistent visualization (using actual group names)
fixed_colors = {
    'CONTROL': '#1f77b4',      # blue
    'αα/--SEA': '#ff7f0e',     # orange
    'αα/-α3.7': '#2ca02c',     # green
    'αα/-α4.2': '#d62728',     # red
}

# ----------------------------
# Process First Dataset
# ----------------------------
df1 = pd.read_excel('200bp_new_run_v2.xlsx', sheet_name='200bp_new_run')
# Apply QC filtering
df1 = df1[df1['Median Depth QC Status'] == 'Pass']
# Save rows with mean_r1 or mean_r2 > 1.25
filtered_rows1 = df1[(df1['mean_r1'] > 1.25) | (df1['mean_r2'] > 1.25)]
filtered_rows1.to_excel('filtered_output_full_df.xlsx', index=False)

# Drop NA values
df_sel1 = df1.dropna(subset=['mean_r1', 'mean_r2', 'Group'])
n1 = len(df_sel1)

# Plot 1: First dataset, colored by Group
plt.figure(figsize=(8, 6))

# Get unique groups and plot each with fixed color (default to black if not found)
for group in sorted(df_sel1['Group'].unique()):
    sub = df_sel1[df_sel1['Group'] == group]
    color = fixed_colors.get(group, '#000000')  # Default to black if group not found
    plt.scatter(sub['mean_r1'], sub['mean_r2'], 
                label=group, alpha=0.7,
                color=color)

plt.xlabel('mean_r1')
plt.ylabel('mean_r2')
plt.title(f'200bp_new_run: Colored by Group (n={n1})')
plt.legend(title='Group', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xlim(*xlims)
plt.ylim(*ylims)
plt.xticks(xticks)
plt.yticks(yticks)
plt.tight_layout()
plt.savefig('200bp_new_run_by_Group.png', dpi=300, bbox_inches='tight')
plt.show()

# ----------------------------
# Process Second Dataset
# ----------------------------
df2 = pd.read_excel('200bp_new_run.xlsx', sheet_name='1684_lr')
# Apply QC filtering
df2 = df2[df2['Median Depth QC Status'] == 'Pass']

# Save rows with mean_r1 or mean_r2 > 1.25
filtered_rows2 = df2[(df2['mean_r1'] > 1.25) | (df2['mean_r2'] > 1.25)]
filtered_rows2.to_excel('1684_above_125r1r2_df.xlsx', index=False)

# Drop NA values
df_sel2 = df2.dropna(subset=['mean_r1', 'mean_r2', 'Group'])
n2 = len(df_sel2)

# Plot 2: Second dataset, colored by Group
plt.figure(figsize=(8, 6))

for group in sorted(df_sel2['Group'].unique()):
    sub = df_sel2[df_sel2['Group'] == group]
    color = fixed_colors.get(group, '#000000')
    plt.scatter(sub['mean_r1'], sub['mean_r2'], 
                label=group, alpha=0.7,
                color=color)

plt.xlabel('mean_r1')
plt.ylabel('mean_r2')
plt.title(f'1684_lr: Colored by Group (n={n2})')
plt.legend(title='Group', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xlim(*xlims)
plt.ylim(*ylims)
plt.xticks(xticks)
plt.yticks(yticks)
plt.tight_layout()
plt.savefig('1684_lr_by_Group.png', dpi=300, bbox_inches='tight')
plt.show()

# ----------------------------
# Process Third Dataset
# ----------------------------
df3 = pd.read_excel('200bp_new_run.xlsx', sheet_name='169')
# Apply QC filtering
df3 = df3[df3['Median Depth QC Status'] == 'Pass']

# Save rows with mean_r1 or mean_r2 > 1.25
filtered_rows3 = df3[(df3['mean_r1'] > 1.25) | (df3['mean_r2'] > 1.25)]
filtered_rows3.to_excel('169_above_125r1r2_df.xlsx', index=False)

# Drop NA values
df_sel3 = df3.dropna(subset=['mean_r1', 'mean_r2', 'Group'])
n3 = len(df_sel3)

# Plot 3: Third dataset, colored by Group
plt.figure(figsize=(8, 6))

for group in sorted(df_sel3['Group'].unique()):
    sub = df_sel3[df_sel3['Group'] == group]
    color = fixed_colors.get(group, '#000000')
    plt.scatter(sub['mean_r1'], sub['mean_r2'], 
                label=group, alpha=0.7,
                color=color)

plt.xlabel('mean_r1')
plt.ylabel('mean_r2')
plt.title(f'169: Colored by Group (n={n3})')
plt.legend(title='Group', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xlim(*xlims)
plt.ylim(*ylims)
plt.xticks(xticks)
plt.yticks(yticks)
plt.tight_layout()
plt.savefig('169_by_Group.png', dpi=300, bbox_inches='tight')
plt.show()