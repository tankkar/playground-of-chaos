import pandas as pd
import matplotlib.pyplot as plt

# full data plot
df = pd.read_excel('lr_validation_result_20250617.copy.xlsx',
                   sheet_name='short read result - new model')

df = pd.read_excel('200bp_new_run.xlsx', sheet_name='169')

filtered_rows = df[(df['mean_r1'] > 1.25) | (df['mean_r2'] > 1.25)]
filtered_rows.to_excel('filtered_output_full_df.xlsx', index=False)

# exact-match filter
wanted = ['3.7K', '4.2K', 'SEA', "CONTROL"]
df_sel = df[df['First label'].isin(wanted)]

# 2D plot
plt.figure(figsize=(8,6))
for lbl in df_sel['final_label'].unique():
    sub = df_sel[df_sel['final_label'] == lbl]
    plt.scatter(sub['mean_r1'], sub['mean_r2'], label=lbl, alpha=0.7)

plt.xlabel('mean_r1')
plt.ylabel('mean_r2')
plt.title('Exact First labels in {3.7K,4.2K,SEA,CONTROL}, coloured by Final Label')
plt.legend(bbox_to_anchor=(1.05,1), loc='upper left', title='Final Label')
plt.tight_layout()
plt.show()

########################
# Get the distribution of final_label
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_excel('lr_validation_result_20250617.copy.xlsx',
sheet_name='short read result - new model')


label_counts = df['final_label'].value_counts()

# Convert to a DataFrame for better formatting
label_distribution = pd.DataFrame({
    'final_label': label_counts.index,
    'count': label_counts.values,
    'percentage': (label_counts.values / len(df) * 100).round(2)
})

# Sort by count in descending order (optional)
label_distribution = label_distribution.sort_values('count', ascending=False)

# Display the distribution table
print(label_distribution)

# Export to Excel if needed
label_distribution.to_excel('final_label_distribution.xlsx', index=False)