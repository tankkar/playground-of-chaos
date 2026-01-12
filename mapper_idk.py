import pandas as pd
import re

# Load the data
temp_df = pd.read_csv('genomic.tsv', sep='\t')
mapper_df = pd.read_excel('sequencing_organizer.xlsx', sheet_name='HKGP')

# Enhanced function to extract sample ID prefix based on patterns
def extract_sample_id(filename):
    # If a hyphen is present, take the part before the first hyphen
    if '-' in filename:
        return filename.split('-')[0]
    # If no hyphen, try to find a pattern resembling Sample ID
    match = re.search(r'[A-Z]\d{7}B\d{2}', filename)
    return match.group(0) if match else None

# Apply the enhanced extraction function to create 'Sample_Num' in temp_df
temp_df['Sample_Num'] = temp_df['file_name'].apply(extract_sample_id)


temp_df = temp_df.sort_values(by=['SRE_ID', 'Sample_Num'], ascending=[True, False])

temp_df = temp_df.drop_duplicates(subset='SRE_ID', keep='first')

# Merge temp_df with mapper_df on 'Sample_Num' and 'Sample ID'
merged_df = temp_df.merge(
    mapper_df[['Sample ID', 'Ref ID', 'Relationship', 'Sex']],
    left_on='Sample_Num',
    right_on='Sample ID',
    how='left'
)

# Select the required columns for the final output
final_df = merged_df[['SRE_ID', 'Sample ID', 'Ref ID', 'Relationship', 'Sex']]

# Output the final dataframe
print(final_df)

# Optionally, save the final dataframe to a new file
final_df.to_csv('final_output.csv', index=False)
