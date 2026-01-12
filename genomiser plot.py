import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re

# Load the CSV file
file_path = 'your_csv_file.csv'  # Replace with the actual file path
df = pd.read_csv(file_path)

# Function to strip non-numeric characters and convert to integer
def extract_ranking(rank_str):
    match = re.search(r'\d+', str(rank_str))
    if match:
        return int(match.group(0))
    else:
        return float('inf')  # Return a large number if no valid ranking is found

# Apply the function to the relevant columns
df['Exomiser V12 ranking'] = df['Exomiser V12 ranking (if available)'].apply(extract_ranking)
df['Exomiser V14 ranking'] = df['Exomiser V14 ranking'].apply(extract_ranking)
df['Genomiser V14 ranking'] = df['Genomiser V14 ranking'].apply(extract_ranking)

# Count how many genomes have the disease variant as a top hit for top 1, top 5, and top 10
def count_top_hits(rankings, top_n):
    return sum(1 for rank in rankings if rank <= top_n)

# Calculate the total number of genomes
total_genomes = len(df)

# Calculate percentages for top 1, top 5, and top 10
top_1_percentage = [
    (count_top_hits(df['Exomiser V12 ranking'], 1) / total_genomes) * 100,
    (count_top_hits(df['Exomiser V14 ranking'], 1) / total_genomes) * 100,
    (count_top_hits(df['Genomiser V14 ranking'], 1) / total_genomes) * 100
]

top_5_percentage = [
    (count_top_hits(df['Exomiser V12 ranking'], 5) / total_genomes) * 100,
    (count_top_hits(df['Exomiser V14 ranking'], 5) / total_genomes) * 100,
    (count_top_hits(df['Genomiser V14 ranking'], 5) / total_genomes) * 100
]

top_10_percentage = [
    (count_top_hits(df['Exomiser V12 ranking'], 10) / total_genomes) * 100,
    (count_top_hits(df['Exomiser V14 ranking'], 10) / total_genomes) * 100,
    (count_top_hits(df['Genomiser V14 ranking'], 10) / total_genomes) * 100
]

# Set a color palette for publication quality
palette = sns.color_palette("Set2")

# Plotting
x_labels = ['Exomiser V12', 'Exomiser V14', 'Genomiser V14']
bar_width = 0.25

# Positions of the bars on the x-axis
r1 = range(len(top_1_percentage))
r2 = [x + bar_width for x in r1]
r3 = [x + bar_width for x in r2]

# Create bar chart
plt.figure(figsize=(10, 6))

plt.bar(r1, top_1_percentage, color=palette[0], width=bar_width, edgecolor='grey', label='Top 1')
plt.bar(r2, top_5_percentage, color=palette[1], width=bar_width, edgecolor='grey', label='Top 5')
plt.bar(r3, top_10_percentage, color=palette[2], width=bar_width, edgecolor='grey', label='Top 10')

# Add xticks on the middle of the group bars
plt.xlabel('Method', fontweight='bold')
plt.xticks([r + bar_width for r in range(len(top_1_percentage))], x_labels)

plt.ylabel('Percentage of Genomes with Disease Variant as Top Hit (%)')
plt.title('Evaluation of Variant Prioritization Tools in Disease Variant Detection')
plt.ylim(0, 100)

# Make the plot look more publication-quality
plt.grid(axis='y', linestyle='--', alpha=0.7)

plt.legend()
plt.tight_layout()
plt.show()
















-----------------------------------------------------------------


df_filtered = df[df['Analytic approach'].notna() & df['Analytic approach'].str.strip().astype(bool)]

analytic_approach_counts = df_filtered['Analytic approach'].value_counts()

plt.figure(figsize=(8, 8))
plt.pie(analytic_approach_counts, labels=analytic_approach_counts.index, autopct='%1.1f%%', colors=sns.color_palette("Set3"))
plt.title('Distribution of Analytic Approaches Used for Pathogenic Variant Detection')
plt.tight_layout()

output_pie_chart_path = "/mnt/data/analytic_approaches_pie_chart.png"
plt.savefig(output_pie_chart_path, dpi=300)
plt.show()